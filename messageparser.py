#!/usr/bin/env python

'''
    **************************************
    messageparser.py (part of freespeech.py)
    **************************************

Message Frames Structure:
    A.B.C.D.TYPE.LEN.LEN.BDY.BDY---.BDY.BDY.D.C.B.A        

class Parser(object)
    Provides parsing message utilities
        bof(): returns true if the message begins with the bof bytes
        eof(): returns true if the message ends with the eof bytes
        len(): returns the len as described in the message body (expected length)
        valid(): returns true if message begins and ends correctly and expected 
                 length == real length
        body(): returns a tuple (type, body) 
                body = the message body i.e. without the bof, eof, type and the 
                length

class Packer(object)
    Receives messages or parts of messages and pack them and put them in 
    the provided queue when they are ready, i.e. message  valid and complete.
    __init__(self, queue)
        expect an instanse of Queue.Queue() or any other object that has 'put' 
        method
        
        
# Copyrights (c) - 2008

'''

__author__ = 'Tzury Bar Yochay'
__version__ = '0.1'
__license__ = 'GPLv3'
__all__ = ['MessageFactory', 'Parser', 'Packer']


import struct
from utils import Storage
from messages import *


MessageFactory = Storage ({
    '\x01': LoginRequest,
    '\x02': LoginReply
})

# Parser.body returns a tuple of (type, buffer) 
# Therefore you can call MessageFactory.create(*Parser.body(msg))
MessageFactory.create = lambda _type, _buffer: MessageFactory[_t](buf=_buffer)
    
class Parser(object):
    '''Provides parsing message utilities'''
    BOF, EOF = '\xab\xcd', '\xdc\xba'
    typos, lenpos = (2,4) , (4, 6)
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
            buf = create_string_buffer(self.length(msg))
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
            