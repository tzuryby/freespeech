#!/usr/bin/env python

'''
    **************************************
    Message (part of freespeech.py)
    **************************************

Message Structure:
    A.B.C.D.LEN.LEN.BDY.BDY---.BDY.BDY.D.C.B.A        

class Parser()
    Provides parsing message utilities
        bof(): returns true if the message begins with the bof bytes
        eof(): returns true if the message ends with the eof bytes
        len(): returns the len as described in the message body (expected length)
        valid(): returns true if message begins and ends correctly and expected length == real length
        body(): returns the message body i.e. without the bof, eof and the length

class Packer()
    Receives messages or parts of messages and pack them and put them in 
    the provided queue when they are ready, i.e. message  valid and complete.
    __init__(self, queue)
        expect an instanse of Queue.Queue()
'''

__author__ = 'Tzury Bar Yochay'
__version__ = '0.1'
__license__ = 'GPLv3'
__all__ = ['Parser', 'Packer']


import struct
import Queue
from utils import Storage

class Parser(object):
    '''Provides parsing message utilities'''
    def __init__(self, format=None):
        self.format = format or \
            Storage(lenpos = (2, 4), bof = '\xab\xcd',  eof = '\xdc\xba')
        self.format.boflen = len(self.format.bof)
        self.format.eoflen = len(self.format.eof)
        
    def bof(self, msg):
        return self.format.bof == msg[:self.format.boflen]
        
    def eof(self, msg):
        return self.format.eof == msg[-self.format.eoflen:]

    def len(self, msg):
        try:
            return struct.unpack('!h', msg[self.format.lenpos[0]:self.format.lenpos[1]])[0]
        except:
            return -1
        
    def valid(self, msg):
        return self.bof(msg) and self.eof(msg) and self.len(msg) == len(msg)
        
    def body(self, msg):
        return self.valid(msg) and msg[self.format.lenpos[1] : -self.format.eoflen]
            

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
    import doctest
    doctest.testmod()
    