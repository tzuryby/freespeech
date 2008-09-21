
import struct
import re

from utils import Storage
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

class IPv4Field(ByteField):
    def __init__(self, start):
        ByteField.__init__(self, start, '!16b')
        
class BaseMessage(object):
    def __init__(self, seq = [], **kwargs):
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
    def __init__(self, **kwargs):
        seq = [
            ('username_length', ByteField, 0, '!b'), 
            ('username', StringField, 1, lambda: '!%dc' % self.username_length.value ), 
            ('password', StringField, lambda: self.username.end(), '!20c'), 
            ('local_ip', IPv4Field, lambda: self.password.end()), 
            ('local_port', IntField, lambda: self.local_ip.end())
        ]
        
        BaseMessage.__init__(self, seq, **kwargs)
    
if __name__ == '__main__':
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
