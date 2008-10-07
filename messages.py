#!/usr/bin/env python

'''
    **************************************
    messages.py (part of freespeech.py)
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
        
Copyrights - 2008

'''

__author__ = 'Tzury Bar Yochay'
__version__ = '0.1'
__license__ = 'GPLv3'
__all__ = ['BaseMessage', 'ByteField', 'ChangeStatus', 'CharField', 'ClientAnswer', 
    'ClientHangupRequest', 'ClientHangupRequestAck', 'ClientInvite', 'ClientInviteAck', 
    'ClientRTP', 'CommMessage', 'Field', 'Hangup', 'IPField', 'IntField', 'KeepAlive', 
    'KeepAliveAck', 'LoginReply', 'LoginRequest', 'Logout', 'ServerForwardAnswer', 
    'ServerForwardHangupRequest', 'ServerForwardInvite', 'ServerForwardRing', 
    'ServerHangupRequestAck', 'ServerOverloaded', 'ServerRTPRelay', 
    'ServerRejectInvite', 'ShortField', 'ShortResponse', 'StringField', 'UUIDField']
    
    #~ ['CommMessage', 'Field', 'ByteField', 'CharField', 'ShortField', 'IntField', 
    #~ 'StringField', 'IPField', 'BaseMessage', 'LoginRequest', 'LoginReply', 
    #~ 'ServerOverloaded', 'Logout', 'KeepAlive', 'KeepAliveAck', 'ClientInvite', 
    #~ 'ServerRejectInvite', 'ServerForwardInvite', 'ClientAckInvite', 
    #~ 'ServerForwardRing', 'SyncAddressBook', 'ShortResponse']
    
import struct, uuid
from ctypes import create_string_buffer
from md5 import new as md5
from decorator import printargs


class CommMessage(object):
    '''Wrapping message with additional data.
    Encapsulates the address, the type and the context for the message
    '''
    def __init__(self, addr, msg_type, body):
        self.addr = addr
        self.msg_type = msg_type
        self.body = body
        self.msg = msg_type(buf=body)        
        self.client_ctx = None
        
        # for login request create new context, for others extract from the message
        if (hasattr(self.msg, 'client_ctx')):
            self.client_ctx = self.msg.client_ctx
        elif isinstance(self.msg, (LoginRequest,)):
            self.client_ctx = md5(str(self.msg.username)).digest()
            
        self.call_ctx = hasattr(self.msg, 'call_ctx') and self.call_ctx
        
    def __repr__(self):
        return 'from %s <%s>, type %s, msg %s' % (self.addr, self.client_ctx, self.msg_type, self.body)
        
class Field(object):    
    def __init__(self, start, format):
        self._value = None      # value of the field
        self.start = start      # starting position on the buffer
        self.format = format    # pack/unpack format
        self.length = struct.calcsize(self.format)
        self.end = self.start + self.length
        
    def pack_into(self, buf):
        '''packs the value into a supplied buffer'''
        struct.pack_into(self.format, buf, self.start, *self._value)
        
    def unpack_from(self, buf):
        '''unpack the value from a supplied buffer'''
        self.value = struct.unpack_from(self.format, buf, self.start)
    
    def __setattr__(self, k, v):
        '''a wrapper around x.value ensure _value will always be a tuple'''
        if k == 'value':
            self._value = isinstance(v, tuple) and v or (v,)
        else:
            self.__dict__[k] = v
        
    def __getattr__(self, k):
        if k == 'value':
            return len(self._value) == 1 and self._value[0] or self._value
        else:
            raise AttributeError
            
    def __repr__(self):
        return str(self._value)
        
    def length(self):
        return struct.calcsize(self.format)
        
class ByteField(Field):
    def __init__(self, start):
        Field.__init__(self, start, '!b')
    
class CharField(Field):
    def __init__(self, start):
        Field.__init__(self, start, '!c')
    
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
            
class UUIDField(StringField):
    def __init__(self, start):
        StringField.__init__(self, start, '!16c')
        
class IPField(Field):
    def __init__(self, start):
        Field.__init__(self, start, '!16b')
        
    def __setattr__(self, k, v):
        '''a wrapper around x.value'''
        if k == 'value':
            if type(v).__name__ == 'str':
                v = [int(o) for o in v.split('.')] + [0, 0, 0, 0, 0, 
                    0, 0, 0, 0, 0, 0, 0]
                self._value = v
            else:
                self._value = v
        else:
            self.__dict__[k] = v
            
class BaseMessage(object):
    def __init__(self, seq = [], *args, **kwargs):
        self.seq = seq
        self.buf = None
        
        if 'buf' in kwargs:
            self._init_buffer(kwargs['buf'])
            self.deserialize()
            
        elif 'length' in kwargs:
            self.buf = create_string_buffer(kwargs['length'])   
            
    def _init_buffer(self, newbuffer=None):
        
        if not self.buf and not newbuffer:
            length = sum((self.dict[field[0]].length for field in self.seq))
            self.buf = create_string_buffer(length)
            
        elif newbuffer:
            # self.buf never initiated
            if not self.buf:
                self.buf = create_string_buffer(len(newbuffer))
                
            # assign or copy the value into self.buf
            if hasattr(newbuffer, 'raw'):
                self.buf = newbuffer
                
            # convert string into writeable-buffer
            elif isinstance(newbuffer,str):
                self.buf.raw = newbuffer
                
        #~ elif not self.buf:
            #~ length = sum((self.__dict__[p[0]].length for p in self.seq))
            #~ self.buf = create_string_buffer(length)
            
    def deserialize(self, buf=None):
        if buf:
            self._init_buffer(buf)
            
        if self.buf:
            for params in self.seq:
                key, ctr, start = params[0], params[1] , params[2]
                format = len(params) == 4 and params[3] or None
                # in case of starting point is a callable
                if hasattr(start, '__call__'):
                    start = start()
                # in case of format is a callable
                if format:
                    if hasattr(format, '__call__'):
                        format = format()
                    self.__dict__[key] = ctr(start, format)
                else:
                    self.__dict__[key] = ctr(start)
                    
                self.__dict__[key].unpack_from(self.buf)
                
    def set_values(self, **kwargs):
        for params in self.seq:
            if params[0] in kwargs:
                key, ctr, start, format = params[0], params[1] , params[2], None                
                start = hasattr(start, '__call__') and start() or start
                args = [start]
                if len(params) == 4:
                    format = params[3]
                if format:
                    if hasattr(format, '__call__'): 
                        format = format()
                    args.append(format)
                    
                self.__dict__[key] = ctr(*args)
                self.__dict__[key].value = kwargs[key]
        
    def serialize(self):
        self._init_buffer()
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
            ('client_ctx', UUIDField, 0),
            ('client_public_ip', IPField, 16), 
            ('client_public_port', IntField, lambda: self.client_public_ip.end),
            ('ctx_expire', IntField, lambda: self.client_public_port.end),
            ('num_of_codecs', ByteField, lambda: self.ctx_expire.end),
            ('codec_list', StringField, lambda: self.num_of_codecs.end, lambda: '!%dc' % self.num_of_codecs.value)]
            
        BaseMessage.__init__(self, seq, *args, **kwargs)

class ServerOverloaded(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [('alternate_ip', IPField, 0)]
        
        BaseMessage.__init__(self, seq, *args, **kwargs)

class Logout(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [('client_ctx', UUIDField, 0)]
        
        BaseMessage.__init__(self, seq, *args, **kwargs)
    
class KeepAlive(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [
            ('client_ctx', UUIDField, 0),
            ('client_public_ip', IPField, 16), 
            ('client_public_port', IntField, lambda: self.client_public_ip.end)]
        
        BaseMessage.__init__(self, seq, *args, **kwargs)

class KeepAliveAck(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [
            ('client_ctx', UUIDField, 0),
            ('expire', IntField, 16),
            ('refresh_contact_list', ByteField, lambda: self.expire.end)]
        
        BaseMessage.__init__(self, seq, *args, **kwargs)
        
class ClientInvite(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [
            ('client_ctx', UUIDField, 0),
            ('other_name_length', ByteField, 16),
            ('other_name', StringField, 17, lambda: '!%dc' % self.other_name_length.value),
            ('num_of_codecs', ByteField, lambda: self.other_name.end),
            ('codec_list', StringField, lambda: self.num_of_codecs.end, lambda: '!%dc' % self.num_of_codecs.value)]
        
        BaseMessage.__init__(self, seq, *args, **kwargs) 
        
class ServerRejectInvite(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [
            ('client_ctx', UUIDField, 0),
            ('error_code', ShortField, 16)]
        
        BaseMessage.__init__(self, seq, *args, **kwargs)

class ServerForwardInvite(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [
            ('client_ctx', UUIDField, 0),
            ('call_ctx', UUIDField, lambda: self.client_ctx.end),
            ('call_type', ByteField, lambda: self.call_ctx.end),
            ('client_name_length', ByteField, lambda: self.call_type.end),
            ('client_name', StringField, lambda: self.client_name_length.end, lambda: '!%dc' % self.client_name_length.value),
            ('client_public_ip', IPField, lambda: self.client_name.end), 
            ('client_public_port', IntField, lambda: self.client_public_ip.end),
            ('num_of_codecs', ByteField, lambda: self.client_public_port.end),
            ('codec_list', StringField, lambda: self.num_of_codecs.end, lambda: '!%dc' % self.num_of_codecs.value)]
        
        BaseMessage.__init__(self, seq, *args, **kwargs) 
        
class ClientInviteAck(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [
            ('client_ctx', UUIDField, 0),
            ('call_ctx', UUIDField, lambda: self.client_ctx.end),
            ('client_status', ByteField, lambda: self.call_ctx.end),
            ('client_public_ip', IPField, lambda: self.client_status.end), 
            ('client_public_port', IntField, lambda: self.client_public_ip.end)]
        
        BaseMessage.__init__(self, seq, *args, **kwargs)

class ServerForwardRing(ClientInviteAck):
    pass

class ClientAnswer(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [
            ('client_ctx', UUIDField, 0),
            ('call_ctx', UUIDField, lambda: self.client_ctx.end),
            ('codec', ByteField, lambda: self.call_ctx.end)]
        
        BaseMessage.__init__(self, seq, *args, **kwargs)
        
class ServerForwardAnswer(ClientAnswer):
    pass
    
class ClientRTP(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [
            ('client_ctx', UUIDField, 0),
            ('call_ctx', UUIDField, lambda: self.client_ctx.end),
            ('rtp_bytes', StringField, lambda: self.call_ctx.end, 1024*4)]
        
        BaseMessage.__init__(self, seq, *args, **kwargs)
        
class ServerRTPRelay(ClientRTP):
    pass
    
class Hangup(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [
            ('client_ctx', UUIDField, 0),
            ('call_ctx', UUIDField, lambda: self.client_ctx.end)]
            
        BaseMessage.__init__(self, seq, *args, **kwargs)
            
class ClientHangupRequest(Hangup):
    pass
    
class ServerForwardHangupRequest(Hangup):
    pass
    
class ClientHangupRequestAck(Hangup):
    pass
    
class ServerHangupRequestAck(Hangup):
    pass

class ChangeStatus(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [
            ('client_ctx', UUIDField, 0),
            ('status', ByteField, lambda: self.client_ctx.end)]
        
        BaseMessage.__init__(self, seq, *args, **kwargs)
        
class ShortResponse(BaseMessage):
    def __init__(self, *args, **kwargs):
        seq = [
            ('client_ctx', UUIDField, 0),
            ('result', ShortField, 16)]
        BaseMessage.__init__(self, seq, *args, **kwargs)
        
        
if __name__ == '__main__':
    ka =KeepAliveAck()
    buf = uuid.uuid4().bytes
    buf += '\x01\x01\x01\x01'
    ka.deserialize(buf)
    print ''.join(ka.client_ctx.value)
    print ka.expire.value
