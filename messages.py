#!/usr/bin/env python
# -*- coding: UTF-8 -*-

'''
**************************************
messages.py (part of freespeech.py)
**************************************
'''

__author__ = 'Tzury Bar Yochay'
__version__ = '0.1'
__license__ = 'GPLv3'
__all__ = ['Parser', 'MessageFramer', 'BaseMessage', 'ByteField', 'CharField', 'ClientAnswer', 
    'CallHangup', 'CallHangupAck', 'ClientInvite', 'ClientInviteAck', 
    'ClientRTP', 'CommMessage', 'Field', 'IPField', 'IntField', 'KeepAlive', 
    'KeepAliveAck', 'LoginReply', 'LoginRequest', 'Logout', 'SignalingMessage', 
    'ServerForwardInvite', 
    'ServerForwardRing', 'ServerOverloaded', 
    'ServerRejectInvite', 'ShortField', 'ShortResponse', 'StringField', 
    'UUIDField', 'MessageTypes', 'string_to_ctx']
    
import struct, uuid, sys
from ctypes import create_string_buffer
from md5 import new as md5
from decorators import printargs
from utils import Storage

def string_to_ctx(*args):
    v = ''.join(args)
    return md5(v).digest()



MessageFactory = Storage(
    create= lambda msg_type, buf: msg_type in MessageTypes and MessageTypes[msg_type](buf=buf) or None )

class Parser(object):
    def __init__(self):
        self.framer = MessageFramer()
        
    def parse_type(self, msg):
        '''parses the type (bytes of typecode)'''
        t = msg[self.framer.TYPE_POS[0]:self.framer.TYPE_POS[1]]
        return t in MessageTypes and t
        
    def bof(self, msg):
        return self.framer.BOF == msg[:self.framer.BOF_LEN]
        
    def eof(self, msg):
        return self.framer.EOF == msg[-self.framer.EOF_LEN:]

    def length(self, msg):
        try:
            return struct.unpack('!h', msg[self.framer.LEN_POS[0]:self.framer.LEN_POS[1]])[0]
        except:
            return -1
        
    def valid(self, msg):
        return self.bof(msg) \
                and self.eof(msg) \
                and self.length(msg) == len(self._body(msg)) \
                and self.parse_type(msg)
        
    def _body(self, msg):
        buf = create_string_buffer(self.length(msg))
        buf.raw = msg[self.framer.LEN_POS[1] : -self.framer.EOF_LEN]
        return buf
        
    def body(self, msg):
        if self.valid(msg):
            return (self.parse_type(msg), self._body(msg))
        else:
            return None

class MessageFramer(object):
    BOF, EOF = '\xab\xcd', '\xdc\xba'
    TYPE_POS, LEN_POS = (2,4) , (4, 6)
    BOF_LEN, EOF_LEN = len(BOF), len(EOF)
    
    def frame(self, type_code, buf):
        length = struct.pack('!h', len(buf))
        return ''.join([self.BOF, type_code, length, buf, self.EOF])
        
message_framer = MessageFramer()

class CommMessage(object):
    '''Wrapping message with additional data.
    Encapsulates the address, the type (ctr) and the context for the message
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
        self.name = name
        
    def pack_into(self, buf):
        '''packs the value into a supplied buffer'''
        try:
            struct.pack_into(self.format, buf, self.start, *self._value)
        except Exception, inst:
            print 'Error @ calling startuct.pack_into with:'
            print 'format', self.format, 'buffer', repr(buf), 'start', self.start, 'value', self._value
        
    def unpack_from(self, buf):
        try:
            '''unpack the value from a supplied buffer'''
            self.value = struct.unpack_from(self.format, buf, self.start)
        except Exception, inst:
            print 'Error @ calling startuct.unpack_from with:'
            print 'format', self.format, 'buffer', repr(buf), 'start', self.start, 'value', self._value
            
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
    '''single byte text field'''
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
            print 'error@StringField.__init__\nstart %s, format %s, name %s' % (
                start, format, name)
            
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
            print 'error@StringField.__setattr__\nname %s, k %s,v %s, format %s, length %s' % (
                self.name, k, v, self.format, self.length)
            
    def __getattr__(self, k):
        if k == 'value':
            return self._value[0:]
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
                v = [int(o) 
                    for o in v.split('.')] + [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0] # 4+12
                self._value = v
            else:
                self._value = v
        else:
            self.__dict__[k] = v
            
class BaseMessage(object):
    seq = [] # the sequence of fields stored in the buffer
    buf = None
    
    def __init__(self, *args, **kwargs):
        try:
            if 'buf' in kwargs:
                self.deserialize(kwargs['buf'])
                
            elif 'length' in kwargs:
                self.buf = create_string_buffer(kwargs['length'])
                
            self.type_code = MessageTypes.keyof(self)
        except:
            print "Unexpected error:", sys.exc_info()[0]
        
    def _init_buffer(self, newbuffer=None):
        try:
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
        except:
            print "Unexpected error:", sys.exc_info()[0]
            
    def _create_buffer(self, length=0):
        try:
            '''alocates a writeable buffer'''
            return create_string_buffer(length)
        except:
            print "Unexpected error:", sys.exc_info()[0]        
        
    def deserialize(self, buf=None):
        try:
            if buf:
                self._init_buffer(buf)
                
            self._set_values(self.seq)        
        except:
            print "Unexpected error:", sys.exc_info()[0]
        
    def set_values(self, **kwargs):
        try:
            items = (p for p in self.seq if p[0] in kwargs)
            self._set_values(items, kwargs)
        except:
            print "Unexpected error:", sys.exc_info()[0]
            
    def dict_fields(self):
        try:
            '''all fields as dict {name: value, ...}'''
            x = dict(
                ((self.__dict__[field[0]].name, 
                        self.__dict__[field[0]].value) for field in self.seq))
            return x
        except:
            print "Unexpected error:", sys.exc_info()[0]        
        
    def _set_values(self, items, values_dict=None):
        try:
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
                
                # set a property as field-name and its value as Field instance.
                self.__dict__[key] = ctr(*args)
                
                # set the value either to a supplied argument or extract from the buffer
                if values_dict:
                    self.__dict__[key].value = values_dict[key]
                else:
                    self.__dict__[key].unpack_from(self.buf)
                    
                #next field starting point
                start = self.__dict__[key].end
        except:
            print "Unexpected error:", sys.exc_info()[0]
            
    def _pack_values(self):
        try:
            '''packs all the values into the buffer'''
            self._init_buffer()
            for v in self.seq:
                self.__dict__[v[0]].pack_into(self.buf)
        except:
            print "Unexpected error:", sys.exc_info()[0]
            
    def serialize(self):
        try:
            '''packs all values into the buffer and returns the buffer'''
            self._pack_values()
            return self.buf.raw
        except:
            print "Unexpected error:", sys.exc_info()[0]        
        
    def __repr__(self):
        return repr(self.pack())
        
    def pack(self):
        try:
            '''packs the buffer and make it ready to ship'''
            return message_framer.frame(self.type_code, self.serialize())
        except:
            print "Unexpected error:", sys.exc_info()[0]
            
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
            
        BaseMessage.__init__(self, *args, **kwargs)

class AlternateServerMessage(BaseMessage):
    pass

    
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
            
        SignalingMessage.__init__(self, *args, **kwargs)
        
class ServerRejectInvite(ShortResponse):
    def __init__(self, *args, **kwargs):
        BaseMessage.__init__(self, *args, **kwargs)
        
        if ('client_ctx' in kwargs or 'reason' in kwargs) and 'buf' not in kwargs:
            self.set_values(client_ctx = kwargs['client_ctx'], reason = kwargs['reason'])
        else:
            print ('Incorrect parameters')
            
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
            
        SignalingMessage.__init__(self, *args, **kwargs)
        
class ClientInviteAck(SignalingMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', UUIDField),
            ('call_ctx', UUIDField),
            ('client_status', CharField),
            ('client_public_ip', IPField),
            ('client_public_port', IntField)]
        
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
            
        SignalingMessage.__init__(self, *args, **kwargs)
    
class ClientAnswer(SignalingMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', UUIDField),
            ('call_ctx', UUIDField),
            ('codec', CharField)]
            
        SignalingMessage.__init__(self, *args, **kwargs)
        
class ClientRTP(BaseMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', UUIDField),
            ('call_ctx', UUIDField),
            ('rtp_bytes', StringField, '!%dc' % (32))]
            
        BaseMessage.__init__(self, *args, **kwargs)
        
class CallHangup(SignalingMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', UUIDField),
            ('call_ctx', UUIDField)]
        BaseMessage.__init__(self, *args, **kwargs)
          
    
class CallHangupAck(CallHangup):
    def __init__(self, *args, **kwargs):
        Hangup.__init__(self, *args, **kwargs)
        
class ServerOverloaded(BaseMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [('alternate_ip', IPField)]
        
        BaseMessage.__init__(self, *args, **kwargs)

MessageTypes = Storage({

    '\x00\x01': ShortResponse,
    '\x00\x02': LoginRequest,
    '\x00\x03': LoginReply,
    '\x00\x04': AlternateServerMessage,
    '\x00\x05': Logout,
    '\x00\x06': KeepAlive,
    '\x00\x07': KeepAliveAck,

    '\x00\x10': ClientInvite,
    '\x00\x11': ServerRejectInvite,
    '\x00\x12': ServerForwardInvite,
    '\x00\x13': ClientInviteAck,
    '\x00\x14': ServerForwardRing,
    '\x00\x15': ClientAnswer,
    
    '\x00\x20': ClientRTP,

    '\x00\x30': CallHangup,
    '\x00\x31': CallHangupAck,
    
    '\x00\xa0': ServerOverloaded
})

def keyof(_v):
    for k,v in MessageTypes.iteritems():
        if isinstance(_v, v) or _v == v:
            return k
            
MessageTypes.keyof = keyof
        
if __name__ == '__main__':
    print repr(MessageTypes.kbv(LoginRequest))