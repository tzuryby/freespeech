#!/usr/bin/env python

'''
    **************************************
    Message (part of freespeech.py)
    **************************************

Message Frames Structure:
    A.B.C.D.TYPE.LEN.LEN.BDY.BDY---.BDY.BDY.D.C.B.A        

class ByteField(object)
    represents a single byte of data stored within a buffer.
    objects attributes:
        start - starting point on the buffer,
        format - the foramt used to pack and unpack,
        length - the len is the result returned by struct.calcsize(format)
    object methods:
        end() - ending point on the buffer (start + len)
        pack_into(buffer) - calls struct.pack_into by passing the supplied buffer and self properties
        unpack_from(buffer) - calls struct.unpack_from and assign self.value with the results
        __setattr__ - a wrapper around self.value - at string it assign
        
class ShortField (ByteField)
    represents short integer (two bytes) stored within a buffer.

class IntField (ByteField)
    represents integer (four bytes) stored within a buffer.
    
class StringField (ByteField)
    represent a string (variable number of bytes) stored within a buffer

class IPField (ByteField)
    represents 16 bytes of data represents within a buffer
    when using IPv4 only the first four bytes contain data, the rest contain zeros
    
class Parser(object)
    Provides parsing message utilities
        bof(): returns true if the message begins with the bof bytes
        eof(): returns true if the message ends with the eof bytes
        len(): returns the len as described in the message body (expected length)
        valid(): returns true if message begins and ends correctly and expected length == real length
        body(): returns a tuple (type, body) 
                body = the message body i.e. without the bof, eof, type and the length

class Packer(object)
    Receives messages or parts of messages and pack them and put them in 
    the provided queue when they are ready, i.e. message  valid and complete.
    __init__(self, queue)
        expect an instanse of Queue.Queue() or any other object that has 'put' method
'''

__author__ = 'Tzury Bar Yochay'
__version__ = '0.1'
__license__ = 'GPLv3'
__all__ = ['ByteField', 'ShortField', 'IntField', 'StringField', 'IPField', 
    'BaseMessage', 'LoginRequest', 'LoginReply', 'MessageFactory', 
    'Parser', 'Packer']


import struct
import Queue
from ctypes import create_string_buffer

class ByteField(object):
    
    def __init__(self, start=0, format='!c'):
        self._value = None
        self.start = start
        self.format = format
        self.length = struct.calcsize(self.format)
        
    def end(self):
        return self.start + self.length
    
    def pack_into(self, buf):
        struct.pack_into(self.format, buf, self.start, *(self.value))
        
    def unpack_from(self, buf):
        self.value = struct.unpack_from(self.format, buf, self.start)
    
    def __setattr__(self, k, v):
        '''a wrapper around x.value'''
        if k == 'value':
            self._value = v
        else:
            self.__dict__[k] = v
        
    def __getattr__(self, k):
        if k == 'value':
            return self._value
        else:
            raise AttributeError
        
    def __repr__(self):
        return str(self._value)
                
class ShortField(ByteField):
    def __init__(self, start):
        ByteField.__init__(self, start, '!h')

class IntField(ByteField):
    def __init__(self, start):
        ByteField.__init__(self, start, '!i')

class StringField(ByteField):
    def __init__(self, start, format):
        ByteField.__init__(self, start, format)
            
    def __setattr__(self, k, v):
        if k == 'value':
            '''a wrapper around x.value'''
            # if you change the format you must change the length as well.
            self.format = '!%dc' % len(v)
            self.length = struct.calcsize(self.format)
            self._value = ''.join(v)
        else:
            self.__dict__[k] = v
        
    def __getattr__(self, k):
        if k == 'value':
            return (c for c in self._value) #re.findall('.', self._value)
        else:
            raise AttributeError

class IPField(ByteField):
    def __init__(self, start):
        ByteField.__init__(self, start, '!16b')
        
class BaseMessage(object):
    def __init__(self, seq = [], *args, **kwargs):
        self.seq = seq
        self.buf = None
        
        if 'buf' in kwargs:
            self._setbuffer(kwargs['buf'])
            self.deserialize()
            
        elif 'length' in kwargs:
            self.buf = create_string_buffer(kwargs['length'])
    
    def _setbuffer(self, buf):
        if not self.buf:
            self.buf = create_string_buffer(len(buf))
        if type(buf).__name__ == 'str':
            self.buf.raw = buf
        elif hasattr(buf, 'raw'):
            self.buf = buf
        
    def deserialize(self, buf=None):
        if buf:
            self._setbuffer(buf)
        
        if self.buf:
            for params in self.seq:
                key, constructor, start = params[0], params[1] , params[2]
                format = len(params) == 4 and params[3] or None
                # in case of starting point is a lambda expression
                if hasattr(start, '__call__'):
                    start = start()
                # in case of format is a lambda expression
                if format:
                    if hasattr(format, '__call__'):
                        format = format()
                    self.__dict__[key] = params[1](start, format)
                else:
                    self.__dict__[key] = params[1](start)
                    
                self.__dict__[key].unpack_from(self.buf)
                
    def serialize(self):
         for params in self.seq:
             self.__dict__[params[0]].pack_into(self.buf)
               
         return self.buf
        

class LoginRequest(BaseMessage):    
    def __init__(self, *args, **kwargs):
        seq = [
            ('username_length', ByteField, 0, '!b'), 
            ('username', StringField, 1, lambda: '!%dc' % self.username_length.value ), 
            ('password', StringField, lambda: self.username.end(), '!20c'), 
            ('local_ip', IPField, lambda: self.password.end()), 
            ('local_port', IntField, lambda: self.local_ip.end())
        ]
        
        BaseMessage.__init__(self, seq, **kwargs)

class LoginReply(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [
            ('global_ip', IPField, 0), 
            ('local_port', IntField, lambda: self.local_ip.end())
        ]
        
        BaseMessage.__init__(self, seq, **kwargs)


MessageFactory = dict ({
    '\x01': LoginRequest,
    '\x02': LoginReply
})


class Parser(object):
    '''Provides parsing message utilities'''
    BOF, EOF = '\xab\xcd', '\xdc\xba'
    typos, lenpos = (2,3) , (3, 5)
    boflen, eoflen = len(BOF), len(EOF)
    
    def __init__(self):
        pass
        
    def parse_type(self, msg):
        t = msg[self.typos[0]:self.typos[1]]
        return t in MessageFactory and t
        
    def bof(self, msg):
        return self.BOF == msg[:self.boflen]
        
    def eof(self, msg):
        return self.EOF == msg[-self.eoflen:]

    def length(self, msg):
        try:
            return struct.unpack('!h', msg[self.lenpos[0]:self.lenpos[1]])[0]
        except:
            return -1
        
    def valid(self, msg):
        return self.bof(msg) and self.eof(msg) and self.length(msg) == len(msg)
        
    def body(self, msg):
        if self.valid(msg):
            buf = create_string_buffer(self.length())
            buf.raw = msg[self.lenpos[1] : -self.eoflen]
            return (self.parse_type(msg), buf)
        else:
            return None
            
class Packer(object):
    '''Pack parts of message into a message and enqueue it'''
    def __init__(self, queue):
        self.clients = dict()
        self.queue = queue
        self.parser = Parser()
        
    def pack(self, data):
        client, msg = data
        self._recv(client, msg)
        if self.parser.eof(msg):
            # get the whole message
            msg = self.clients[client]
            if self.parser.valid(msg):
                self.queue.put((client, self.parser.body(self.clients[client])))
            del self.clients[client]
        
    # receives the message and store it in the clients[client]
    def _recv(self, client, msg):
        # new client or new message
        if (client not in self.clients or self.parser.bof(msg)):
            self.clients[client] = msg
        else:
            self.clients[client] = self.clients[client] + msg
            
def test_packer():
    '''
        >>> queue = Queue.Queue()
        >>> packer = Packer(queue)
        >>> packer.pack(('client-01', '\xab\xcd\x00'))
        >>> packer.pack(('client-01', '\x08\xcc\xdd'))
        >>> packer.pack(('client-01', '\xdc\xba'))
        >>> queue.get()
        ('client-01', '\xcc\xdd')
        >>> packer.pack(('client-02', '\xab\xcd\x00\x08\x01\xdd\xdc\xba'))
        >>> queue.get()
        ('client-02', '\x01\xdd')
    '''
    pass
    
def test_parser():
    '''
        >>> p = Parser()
        >>> invalid_msg = '\xab\xcd\x00\x08\x01\x01\x01\xdc\xba'
        >>> valid_msg = '\xab\xcd\x00\x08\x01\x01\xdc\xba'
        >>> not p.valid(invalid_msg)
        True
        >>> p.valid(valid_msg)
        True
        >>> Parser().body(valid_msg)
        '\x01\x01'
        >>> Parser().body(invalid_msg)
        False
    '''
    
if __name__ == "__main__":
    # won't work since doctest have a problem parsing the bytes compound the message
    # however these lines were pasted from the toplevel py interperter and worl there fine
    #import doctest
    #doctest.testmod()
    buf = ['\x08'                                                                               # username_length
           '\x71\x72\x73\x74\x75\x76\x77\x78'                                                   # usrname
           '\x72\x73\x74\x75\x76\x77\x78\x79\x69\x68\x67\x66\x70\x71\x72\x73\x74\x75\x76\x77'   # password
            '\x78\x79\x69\x68\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'                  # local_ip
           '\x00\x00\x13\x90']                                                                  # port
    
    buf = ''.join(buf)
    
    print ('='*80)
    
    lr = LoginRequest(buf=buf)
    for i in lr.seq:
        print i[0], '\t', lr.__dict__[i[0]]
    
    
    print ('='*80)
    
    buf2 =  lr.serialize().raw
    assert (buf2 == buf)
    print buf
    print buf2
    
    print ('='*80)
    
    lr = LoginRequest(length=49)
    lr.deserialize(buf)
    for i in lr.seq:
        print i[0], '\t', lr.__dict__[i[0]]
    