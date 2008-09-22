#!/usr/bin/env python

'''
    **************************************
    Message (part of freespeech.py)
    **************************************

Message Frames Structure:
    A.B.C.D.TYPE.LEN.LEN.BDY.BDY---.BDY.BDY.D.C.B.A        

class Field(object)
    represents a single byte of data stored within a buffer.
    objects attributes:
        start - starting point on the buffer,
        format - the foramt used to pack and unpack,
        length - the len is the result returned by struct.calcsize(format)
        end - ending point on the buffer (start + length)
    object methods:
        pack_into(buffer) - calls struct.pack_into by passing the supplied buffer and self properties
        unpack_from(buffer) - calls struct.unpack_from and assign self.value with the results
        __setattr__ - a wrapper around self.value - at string it assign

class ByteField(Field)
    represents a single byte (signed char) of data '!b'
    
class CharField(Field)
    represents a single character '!c'
    
class ShortField (Field)
    represents short integer (two bytes) stored within a buffer.

class IntField (Field)
    represents integer (four bytes) stored within a buffer.
    
class StringField (Field)
    represent a string (variable number of bytes) stored within a buffer

class IPField (Field)
    represents 16 bytes of data represents within a buffer
    when using IPv4 only the first four bytes contain data, the rest contain 
    zeros
    
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
'''

__author__ = 'Tzury Bar Yochay'
__version__ = '0.1'
__license__ = 'GPLv3'

# Copyrights - 2008

__all__ = ['Field', 'ByteField', 'CharField', 'ShortField', 'IntField', 'StringField', 'IPField', 
    'BaseMessage', 'LoginRequest', 'LoginReply', 'ServerOverloaded', 'Logoff', 'KeepAlive', 'KeepAliveAck', 
    'ClientInvite', 'ServerRejectInvite', 'ServerForwardInvite', 'ClientAckInvite', 'ServerForwardRing',
    'MessageFactory', 'Parser', 'Packer']

import struct
from ctypes import create_string_buffer


class Field(object):    
    def __init__(self, start, format):
        self._value = None
        self.start = start
        self.format = format
        self.length = struct.calcsize(self.format)
        self.end = self.start + self.length
        
    def pack_into(self, buf):
        struct.pack_into(self.format, buf, self.start, *self.value)
        
    def unpack_from(self, buf):
        self.value = struct.unpack_from(self.format, buf, self.start)
    
    def __setattr__(self, k, v):
        '''a wrapper around x.value'''
        if k == 'value':
            self._value = isinstance(v, tuple) and v or (v,)
        else:
            self.__dict__[k] = v
        
    def __getattr__(self, k):
        if k == 'value':
            return self._value
        else:
            raise AttributeError
        
    def __repr__(self):
        return str(self._value)
                
class ByteField(Field):
    def __init__(self, start):
        Field.__init__(self, start, '!b')
    
class CharField(Field):
    def __init__(self, start):
        Field.__init__(self, start, '!c')
    
    def raw_value(self):
        return self.value[0]
    
class ShortField(Field):
    def __init__(self, start):
        Field.__init__(self, start, '!h')

class IntField(Field):
    def __init__(self, start):
        Field.__init__(self, start, '!i')

class StringField(Field):
    def __init__(self, start, format):
        Field.__init__(self, start, format)
            
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
            return (c for c in self._value)
        else:
            raise AttributeError

class IPField(Field):
    def __init__(self, start):
        Field.__init__(self, start, '!16b')
        
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
            ('username_length', ByteField, 0), 
            ('username', StringField, 1, lambda: '!%dc' % self.username_length.value ), 
            ('password', StringField, lambda: self.username.end, '!20c'), 
            ('local_ip', IPField, lambda: self.password.end), 
            ('local_port', IntField, lambda: self.local_ip.end)]
            
        BaseMessage.__init__(self, seq, *args, **kwargs)

class LoginReply(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [
            ('client_ctx', StringField, 0, '!16c')
            ('client_public_ip', IPField, 16), 
            ('client_public_port', IntField, lambda: self.client_public_ip.end),
            ('ctx_expire', IntField, lambda: self.client_public_port.end),
            ('num_of_codecs', ByteField, lambda: self.ctx_expire.end),
            ('codec_list', StringField, lambda: self.num_of_codecs.end, lambda: '!%dc' % self.num_of_codecs.value)]
            
        BaseMessage.__init__(self, seq, *args, **kwargs)

class ServerOverloaded(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [('alternate_ip', IPField, 0)]
        
        BaseMEssage.__init__(self, seq, *args, **kwargs)

class Logoff(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [('client_ctx', StringField, 0, '!16c')]
        
        BaseMessage.__init__(self, seq, *args, **kwargs)
    
class KeepAlive(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [
            ('client_ctx', StringField, 0, '!16c')
            ('client_public_ip', IPField, 16), 
            ('client_public_port', IntField, lambda: self.local_ip.end)]
        
        BaseMessage.__init__(self, seq, *args, **kwargs)

class KeepAliveAck(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [
            ('client_ctx', StringField, 0, '!16c'),
            ('expire', IntField, 16)]
        
        BaseMessage.__init__(self, seq, *args, **kwargs)
        
class ClientInvite(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [
            ('client_ctx', StringField, 0, '!16c'),
            ('other_name_length', ByteField, 16),
            ('other_name', StringField, 17, lambda: '!%dc' % self.other_name_length.value),
            ('num_of_codecs', ByteField, lambda: self.other_name.end),
            ('codec_list', StringField, lambda: self.num_of_codecs.end, lambda: '!%dc' % self.num_of_codecs.value)]
        
        BaseMessage.__init__(self, seq, *args, **kwargs) 

class ServerRejectInvite(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [
            ('client_ctx', StringField, 0, '!16c'),
            ('error_code', ShortField, 16)]
        
        BaseMessage.__init__(self, seq, *args, **kwargs) 

class ServerForwardInvite(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [
            ('client_ctx', StringField, 0, '!16c'),
            ('other_name_length', ByteField, 16),
            ('other_name', StringField, 17, lambda: '!%dc' % self.other_name_length.value),
            ('client_public_ip', IPField, lambda: self.other_name.end), 
            ('client_public_port', IntField, lambda: self.local_ip.end),
            ('num_of_codecs', ByteField, lambda: self.client_public_port.end),
            ('codec_list', StringField, lambda: self.num_of_codecs.end, lambda: '!%dc' % self.num_of_codecs.value)]
        
        BaseMessage.__init__(self, seq, *args, **kwargs) 

class ClientAckInvite(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [
            ('client_ctx', StringField, 0, '!16c')
            ('client_status', ByteField, 16)
            ('client_public_ip', IPField, 17), 
            ('client_public_port', IntField, lambda: self.public_ip.end)]
        
        BaseMessage.__init__(self, seq, *args, **kwargs)

class ServerForwardRing(ClientAckInvite):
    pass
