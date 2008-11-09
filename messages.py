#!/usr/bin/env python

'''
**************************************
messages.py (part of freespeech.py)
**************************************

Message Frames Structure:
    A.B.C.D.TYPE.LEN.LEN.BDY.BDY...BDY.BDY.D.C.B.A        

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
    'KeepAliveAck', 'LoginReply', 'LoginRequest', 'Logout', 'SignalingMessage', 
    'ServerForwardAnswer', 'ServerForwardHangupRequest', 'ServerForwardInvite', 
    'ServerForwardRing', 'ServerHangupRequestAck', 'ServerOverloaded', 'ServerRTPRelay', 
    'ServerRejectInvite', 'ShortField', 'ShortResponse', 'StringField', 
    'UUIDField', 'MessageTypes', 'string_to_ctx']
    
import struct, uuid
from ctypes import create_string_buffer
from md5 import new as md5
from decorators import printargs


def string_to_ctx(*args):
    v = ''.join(args)
    return md5(v).digest()

def frame_msg(type_code, buf):
    BOF, EOF = '\xab\xcd', '\xdc\xba'
    length = struct.pack('!h', len(buf))
    return ''.join([BOF, type_code, length, buf, EOF])


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
            self.client_ctx = self.msg.client_ctx.value
            
        elif isinstance(self.msg, (LoginRequest,)):
            client_ctx = string_to_ctx(self.msg.username.value)
            print 'creating a client_ctx ->', 'username:' , self.msg.username.value, 'ctx:', client_ctx, '<-'
            self.client_ctx = client_ctx
            
        self.call_ctx = hasattr(self.msg, 'call_ctx') and self.msg.call_ctx.value
        
    def __repr__(self):
        return 'from %s <%s>, type %s, msg %s' % (self.addr, self.client_ctx, self.msg_type, self.msg.__repr__())
        
class Field(object):
    def __init__(self, start, format, name=None):
        self._value = None      # value of the field
        self.start = start      # starting position on the buffer
        self.format = format    # pack/unpack format
        self.length = struct.calcsize(self.format)
        self.end = self.start + self.length
        if name: self.name = name
        
    def pack_into(self, buf):
        '''packs the value into a supplied buffer'''
        #print 'name format start _value:', self.name, self.format, self.start, self._value
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
        '''for single value return tuple[0], otherwise, return the tuple'''
        if k == 'value':
            return len(self._value) == 1 and self._value[0] or self._value
        else:
            raise AttributeError
            
    def __repr__(self):
        '''string representation of the tuple'''
        return self._value
        
class ByteField(Field):
    '''single byte numeric field'''
    def __init__(self, start, name=None):
        Field.__init__(self, start, '!b', name)
        
class CharField(Field):
    '''single byte textual field'''
    def __init__(self, start, name=None):
        Field.__init__(self, start, '!c', name)
        
class ShortField(Field):
    '''2 bytes numeric field'''
    def __init__(self, start, name=None):
        Field.__init__(self, start, '!h', name)
        
class IntField(Field):
    '''4 bytes numeric field'''
    def __init__(self, start, name=None):
        Field.__init__(self, start, '!i', name)
        
class StringField(Field):
    '''variable length string'''
    def __init__(self, start, format, name=None):
        try:
            Field.__init__(self, start, format, name)
        except:
            print 'error@StringField.__init__'
            print 'start %s, format %s, name %s' %(start, format, name)
            
    def __setattr__(self, k, v):
        try:
            if k == 'value':
                '''a wrapper around x.value'''
                # if you change the format you must change the length as well.
                self.format = '!%dc' % len(v)
                self.length = struct.calcsize(self.format)
                self._value = ''.join(v)
            else:
                self.__dict__[k] = v
        except:
            print 'error@StringField.__setattr__'
            print 'name %s, k %s,v %s, format %s, length %s' % (self.name, k, v, self.format, self.length)
            
    def __getattr__(self, k):
        if k == 'value':
            return self._value[0:] #(c for c in self._value)
        else:
            raise AttributeError
            
class UUIDField(StringField):
    '''16 bytes uniqueue_id'''
    def __init__(self, start, name=None):
        StringField.__init__(self, start, '!16c', name)
        
class IPField(Field):
    '''16 bytes for IPv6, in IPv4 only the first 4 bytes are used'''
    def __init__(self, start, name=None):
        Field.__init__(self, start, '!16b', name)
        
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
    seq = [] # the sequence of fields stored in the buffer
    buf = None
    
    def __init__(self, *args, **kwargs):        
        if 'buf' in kwargs:
            self._init_buffer(kwargs['buf'])
            self.deserialize()
            
        elif 'length' in kwargs:
            self.buf = create_string_buffer(kwargs['length'])
            
    def _init_buffer(self, newbuffer=None):
        if not self.buf and not newbuffer:
            length = sum((self.__dict__[field[0]].length for field in self.seq))
            self.buf = self._create_buffer(length)
            
        elif newbuffer:
            # self.buf never initialized
            if not self.buf:
                self.buf = self._create_buffer(len(newbuffer))
                
            # assign or copy the string-value into self.buf
            if hasattr(newbuffer, 'raw'):
                self.buf = newbuffer
            elif isinstance(newbuffer,str):
                self.buf.raw = newbuffer
            
    def _create_buffer(self, length=0):
        '''alocates a writeable buffer'''
        return create_string_buffer(length)
        
    def deserialize(self, buf=None):
        if buf:
            self._init_buffer(buf)
            
        self._set_values(self.seq)        
        
    def set_values(self, **kwargs):
        items = (p for p in self.seq if p[0] in kwargs)
        self._set_values(items, kwargs)
        
    def dict_fields(self):
        x = dict(
            ((self.__dict__[field[0]].name, 
                    self.__dict__[field[0]].value) for field in self.seq))
        print 'dict_fields:\n', x
        return x
        
    def _set_values(self, items, values_dict=None):
        start = 0 # first field position
        for params in items:
            key, ctr = params[0], params[1]
            format = len(params) == 3 and params[2]
            args = [start]
            if format:
                if hasattr(format, '__call__'): 
                    format = format()
                args.append(format)
            
            # key -> field.name
            args.append(key)
            
            self.__dict__[key] = ctr(*args)
            
            if values_dict:
                self.__dict__[key].value = values_dict[key]
            else:
                self.__dict__[key].unpack_from(self.buf)
                
            #next field starting point
            start = self.__dict__[key].end
            
    def _pack_values(self):
        self._init_buffer()
        for v in self.seq:
            self.__dict__[v[0]].pack_into(self.buf)
        
    def get_buffer(self):
        '''returns a writeable buffer which contains the values of the object
        call buf.raw in order to get the bytes represented as string
        '''
        self._pack_values()
        return self.buf
        
    def serialize(self):
        self._pack_values()
        ret = frame_msg(self.type_code, self.buf.raw)
        return ret
        
    #~ def buffer_format(self):
        #~ seq_keys = (f[0] for f in self.seq)
        #~ formats = (self.__dict__[f].format for f in seq_keys)
        #~ cleaned = (f.replace('!', '') for f in formats)
        #~ return '!' + ' '.join(cleaned)
        
    def __repr__(self):
        return repr(self.serialize())
        
class ShortResponse(BaseMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', UUIDField),
            ('result', ShortField)]
        BaseMessage.__init__(self, *args, **kwargs)
        
class LoginRequest(BaseMessage):    
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('username_length', ByteField), 
            ('username', StringField, lambda: '!%dc' % self.username_length.value ), 
            ('password', StringField, '!20c'), 
            ('local_ip', IPField), 
            ('local_port', IntField)]
            
        self.type_code = '\x00\x01'
        BaseMessage.__init__(self, *args, **kwargs)
        
class LoginReply(BaseMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', UUIDField),
            ('client_public_ip', IPField),
            ('client_public_port', IntField),
            ('ctx_expire', IntField),
            ('num_of_codecs', ByteField),
            ('codec_list', StringField, lambda: '!%dc' % self.num_of_codecs.value)]
            
        self.type_code = '\x00\x02'
        BaseMessage.__init__(self, *args, **kwargs)

class ServerOverloaded(BaseMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [('alternate_ip', IPField)]
        
        BaseMessage.__init__(self, *args, **kwargs)

class Logout(BaseMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [('client_ctx', UUIDField)]
        
        BaseMessage.__init__(self, *args, **kwargs)
    
class KeepAlive(BaseMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', UUIDField),
            ('client_public_ip', IPField),
            ('client_public_port', IntField)]
        
        BaseMessage.__init__(self, *args, **kwargs)

class KeepAliveAck(BaseMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', UUIDField),
            ('expire', IntField),
            ('refresh_contact_list', ByteField)]
        
        BaseMessage.__init__(self, *args, **kwargs)

class SignalingMessage(BaseMessage):
    def __init__(self, *args, **kwargs):
        BaseMessage.__init__(self, *args, **kwargs)
    
class ClientInvite(SignalingMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', UUIDField),
            ('calle_name_length', ByteField),
            ('calle_name', StringField, lambda: '!%dc' % self.calle_name_length.value),
            ('num_of_codecs', ByteField),
            ('codec_list', StringField, lambda: '!%dc' % self.num_of_codecs.value)]
            
        self.type_code = '\x00\x06'
        SignalingMessage.__init__(self, *args, **kwargs)
        
class ServerRejectInvite(ShortResponse):
    def __init__(self, *args, **kwargs):
        BaseMessage.__init__(self, *args, **kwargs)
        if ('client_ctx' in kwargs or 'reason' in kwargs) and 'buf' not in kwargs:
            self.set_values(client_ctx = kwargs['client_ctx'], reason = kwargs['reason'])
        else:
            raise 'Incorrect parameters'

class ServerForwardInvite(SignalingMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', UUIDField),
            ('call_ctx', UUIDField),
            ('call_type', ByteField),
            ('client_name_length', ByteField),
            ('client_name', StringField, lambda: '!%dc' % self.client_name_length.value),
            ('client_public_ip', IPField),
            ('client_public_port', IntField),
            ('num_of_codecs', ByteField),
            ('codec_list', StringField, lambda: '!%dc' % self.num_of_codecs.value)]
            
        self.type_code = '\x00\x08'
        SignalingMessage.__init__(self, *args, **kwargs)
        
class ClientInviteAck(SignalingMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', UUIDField),
            ('call_ctx', UUIDField),
            ('client_status', CharField),
            ('client_public_ip', IPField),
            ('client_public_port', IntField)]
        
        self.type_code = '\x00\x07'
        
        SignalingMessage.__init__(self, *args, **kwargs)
        
class ServerForwardRing(SignalingMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', UUIDField),
            ('call_ctx', UUIDField),
            ('client_status', CharField),
            ('call_type', ByteField),
            ('client_public_ip', IPField),
            ('client_public_port', IntField)]
            
        self.type_code = '\x00\x0a'
        
        SignalingMessage.__init__(self, *args, **kwargs)
    
class ClientAnswer(SignalingMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', UUIDField),
            ('call_ctx', UUIDField),
            ('codec', CharField)]
            
        self.type_code = '\x00\x0b'
        SignalingMessage.__init__(self, *args, **kwargs)
        
class ServerForwardAnswer(SignalingMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', UUIDField),
            ('call_ctx', UUIDField),
            ('codec', CharField)]
            
        self.type_code = '\x00\x0c'
        SignalingMessage.__init__(self, *args, **kwargs)
        
    def copy_from(self, client_answer):
        self.set_values(**client_answer.dict_fields())
        return self
    
class ClientRTP(BaseMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', UUIDField),
            ('call_ctx', UUIDField),
            ('rtp_bytes', StringField, '!%dc' % (32))]
            
        self.type_code = '\x00\x0d'
        BaseMessage.__init__(self, *args, **kwargs)
        
class ServerRTPRelay(ClientRTP):
    def __init__(self, *args, **kwargs):
        ClientRTP.__init__(self, *args, **kwargs)
        self.type_code = '\x00\x0e'
        
    def copy_from(self, client_rtp):
        self.set_values(**client_rtp.dict_fields())
        return self
        
        
class Hangup(SignalingMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', UUIDField),
            ('call_ctx', UUIDField)]
            
        BaseMessage.__init__(self, *args, **kwargs)
            
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
        self.seq = [
            ('client_ctx', UUIDField),
            ('status', ByteField)]
        
        BaseMessage.__init__(self, *args, **kwargs)
        
MessageTypes = dict({
    '\x00\x01': LoginRequest,
    '\x00\x02': LoginReply,
    '\x00\x03': Logout,
    '\x00\x04': KeepAlive,
    '\x00\x05': KeepAliveAck,
    '\x00\x06': ClientInvite,
    '\x00\x07': ClientInviteAck,
    '\x00\x08': ServerForwardInvite,
    '\x00\x09': ServerRejectInvite,
    '\x00\x0a': ServerForwardRing,
    '\x00\x0b': ClientAnswer,
    '\x00\x0c': ServerForwardAnswer,
    '\x00\x0d': ClientRTP,
    '\x00\x0e': ServerRTPRelay,
    '\x00\xff': ServerOverloaded,
})


        
if __name__ == '__main__':
    ka =KeepAliveAck()
    buf = uuid.uuid4().bytes
    buf += '\x01\x01\x01\x01'
    ka.deserialize('\xab\xcd\x00\x01\x00\x14' + buf + '\xdc\xba')
    x = ka.get_buffer()
    print repr(x.raw)
    print repr(''.join(ka.client_ctx.value))
    print ka.expire.value
    