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

__all__ = [
    'Parser', 
    'Framer', 
    'BaseMessage', 
    'HangupRequest', 
    'HangupRequestAck', 
    'ClientInvite', 
    'ClientAnswer', 
    'ClientInviteAck', 
    'ClientRTP', 
    'CommMessage', 
    'KeepAlive', 
    'KeepAliveAck', 
    'LoginReply', 
    'LoginRequest', 
    'Logout', 
    'SignalingMessage', 
    'ServerForwardInvite', 
    'ServerForwardRing', 
    'ServerOverloaded', 
    'ServerRejectInvite', 
    'ShortResponse', 
    'MessageTypes', 
    'string_to_ctx',
    ]
    
import struct
from ctypes import create_string_buffer, c_int
from utils import Storage
from logger import log
from messagefields import *

def string_to_ctx(*args):
    v = ''.join((str(arg) for arg in args))
    # ensure we use 32 bit integer on 64 bit CPU
    h = c_int(hash(v)).value
    log.debug('hashing %s as %d' % (repr(v), h))
    return h

class Parser(object):
    def __init__(self):
        pass
        
    def parse_type(self, msg):
        '''parses the type (bytes of typecode)'''
        t = msg[Framer.TYPE_POS[0]:Framer.TYPE_POS[1]]
        return t in MessageTypes and t
        
    def bof(self, msg):
        return Framer.BOF == msg[:Framer.BOF_LEN]
        
    def eof(self, msg):
        return Framer.EOF == msg[-Framer.EOF_LEN:]

    def length(self, msg):
        try:
            return struct.unpack(
                '!h', msg[Framer.LEN_POS[0]:Framer.LEN_POS[1]])[0]
        except:
            return -1
        
    def valid(self, msg):
        return (self.bof(msg) 
                and self.eof(msg) 
                and self.length(msg) == len(self._body(msg)) 
                and self.parse_type(msg))
        
    def _body(self, msg):
        buf = create_string_buffer(self.length(msg))
        buf.raw = msg[Framer.LEN_POS[1] : -Framer.EOF_LEN]
        return buf
        
    def body(self, msg):
        '''returns a tuple (msg_type, msg_buffer)'''
        if self.valid(msg):
            return (self.parse_type(msg), self._body(msg))
        else:
            return None

class Framer(object):
    BOF = '\xab\xcd'
    EOF = '\xdc\xba'
    TYPE_POS = (2,4) 
    LEN_POS = (4, 6)
    BOF_LEN = len(BOF)
    EOF_LEN = len(EOF)
    
    @staticmethod
    def frame(type_code, buf):
        length = struct.pack('!h', len(buf))
        return ''.join([Framer.BOF, type_code, length, buf, Framer.EOF])
        
class CommMessage(object):
    '''Wrapps message with additional data.
    Encapsulates the address, the type of the message(Class) 
    and the context fields for the message (client, call)'''
    addr = msg_type = body = msg_type = client_ctx = None

    def __init__(self, addr, msg_type, body):
        self.addr = addr
        self.msg_type = msg_type
        self.body = body
        self.msg = msg_type(buf=body)
        self.client_ctx = None
        
        # for login request create new context, 
        # for others extract from the message
        if (getattr(self.msg, 'client_ctx', None)):
            self.client_ctx = self.msg.client_ctx.value
            
        elif isinstance(self.msg, (LoginRequest,)):
            client_ctx = string_to_ctx(self.msg.username.value)
            log.info('a new client_ctx ', 
                'username: %s ctx: %s' % (
                    self.msg.username.value ,repr(client_ctx)))
            self.client_ctx = client_ctx
            
        self.call_ctx = getattr(self.msg, 'call_ctx', None) \
            and self.msg.call_ctx.value
        
    def __repr__(self):
        return 'from %s <%s>, type %s, msg %s' % (
            self.addr, self.client_ctx, self.msg_type, repr(self.msg))
                    
class BaseMessage(object):
    seq = [] # the sequence of fields stored in the buffer
    buf = None
    
    def __init__(self, *args, **kwargs):
        if 'buf' in kwargs:
            self.deserialize(kwargs['buf'])
            
        elif 'length' in kwargs:
            self.buf = create_string_buffer(kwargs['length'])
            
        self.type_code = MessageTypes.keyof(self)
        
    def _init_buffer(self, newbuffer=None):
        try:
            if not self.buf and not newbuffer:
                length = sum((self.__dict__[field[0]].length 
                    for field in self.seq))
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
            log.exception('exception')
            
    def _create_buffer(self, length=0):
        try:
            '''alocates a writeable buffer'''
            return create_string_buffer(length)
        except:
            log.exception('exception')        
        
    def deserialize(self, buf=None):
        try:
            if buf:
                self._init_buffer(buf)
                
            self._set_values(self.seq)        
        except:
            log.exception('exception')
        
    def set_values(self, **kwargs):
        try:
            items = (p for p in self.seq if p[0] in kwargs)
            self._set_values(items, kwargs)
        except:
            log.exception('exception')
            
    def dict_fields(self):
        try:
            '''all fields as dict {name: value, ...}'''
            x = dict(
                ((self.__dict__[field[0]].name, 
                        self.__dict__[field[0]].value) for field in self.seq))
            return x
        except:
            log.exception('exception')        
        
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
                
                # set the value either to a supplied argument 
                # or extract from the buffer
                if values_dict:
                    self.__dict__[key].value = values_dict[key]
                else:
                    self.__dict__[key].unpack_from(self.buf)
                    
                #next field starting point
                start = self.__dict__[key].end
        except:
            log.exception('exception')
            
    def _pack_values(self):
        try:
            '''packs all the values into the buffer'''
            self._init_buffer()
            for v in self.seq:
                self.__dict__[v[0]].pack_into(self.buf)
        except:
            log.exception('exception')
            
    def serialize(self):
        try:
            '''packs all values into the buffer and returns the buffer'''
            self._pack_values()
            return self.buf.raw
        except:
            log.exception('exception')
        
    def pack(self):
        try:
            '''packs the buffer and make it ready to ship'''
            return Framer.frame(self.type_code, self.serialize())
        except:
            log.exception('exception')
            
class ShortResponse(BaseMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', IntField),
            ('result', ShortField)]
            
        BaseMessage.__init__(self, *args, **kwargs)
        
class LoginRequest(BaseMessage):    
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('username_length', ByteField), 
            ('username', StringField, 
                lambda: '!%dc' % self.username_length.value ), 
            ('password', StringField, '!20c'), 
            ('local_ip', IPField), 
            ('local_port', IntField)]
            
        BaseMessage.__init__(self, *args, **kwargs)
        
class LoginReply(BaseMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', IntField),
            ('client_public_ip', IPField),
            ('client_public_port', IntField),
            ('ctx_expire', IntField),
            ('num_of_codecs', ByteField),
            ('codec_list', StringField, 
                lambda: '!%dc' % self.num_of_codecs.value)]
            
        BaseMessage.__init__(self, *args, **kwargs)

class AlternateServerMessage(BaseMessage):
    pass

    
class Logout(BaseMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [('client_ctx', IntField)]
        BaseMessage.__init__(self, *args, **kwargs)

    
class KeepAlive(BaseMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', IntField),
            ('client_public_ip', IPField),
            ('client_public_port', IntField)]
        
        BaseMessage.__init__(self, *args, **kwargs)

class KeepAliveAck(BaseMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', IntField),
            ('expire', IntField),
            ('refresh_contact_list', ByteField)]
        
        BaseMessage.__init__(self, *args, **kwargs)

class SignalingMessage(BaseMessage):
    def __init__(self, *args, **kwargs):
        BaseMessage.__init__(self, *args, **kwargs)
    
class ClientInvite(SignalingMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', IntField),
            ('calle_name_length', ByteField),
            ('calle_name', StringField, 
                lambda: '!%dc' % self.calle_name_length.value),
            ('num_of_codecs', ByteField),
            ('codec_list', StringField, 
                lambda: '!%dc' % self.num_of_codecs.value)]
            
        SignalingMessage.__init__(self, *args, **kwargs)
        
class ServerRejectInvite(ShortResponse):
    def __init__(self, *args, **kwargs):
        ShortResponse.__init__(self, *args, **kwargs)
        
class ServerForwardInvite(SignalingMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', IntField),
            ('call_ctx', IntField),
            ('call_type', ByteField),
            ('client_name_length', ByteField),
            ('client_name', StringField, 
                lambda: '!%dc' % self.client_name_length.value),
            ('client_public_ip', IPField),
            ('client_public_port', IntField),
            ('num_of_codecs', ByteField),
            ('codec_list', StringField, 
                lambda: '!%dc' % self.num_of_codecs.value)]
            
        SignalingMessage.__init__(self, *args, **kwargs)
        
class ClientInviteAck(SignalingMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', IntField),
            ('call_ctx', IntField),
            ('client_status', CharField),
            ('client_public_ip', IPField),
            ('client_public_port', IntField)]
        
        SignalingMessage.__init__(self, *args, **kwargs)
        
class ServerForwardRing(SignalingMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', IntField),
            ('call_ctx', IntField),
            ('client_status', CharField),
            ('call_type', ByteField),
            ('client_public_ip', IPField),
            ('client_public_port', IntField)]
            
        SignalingMessage.__init__(self, *args, **kwargs)
    
class ClientAnswer(SignalingMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', IntField),
            ('call_ctx', IntField),
            ('codec', CharField)]
            
        SignalingMessage.__init__(self, *args, **kwargs)
        
class ClientRTP(BaseMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', IntField),
            ('call_ctx', IntField),
            ('sequence', IntField),
            ('rtp_bytes_length', ShortField),
            ('rtp_bytes', StringField, 
                lambda: '!%dc' % self.rtp_bytes_length.value)]
            
        BaseMessage.__init__(self, *args, **kwargs)
        
class HangupRequest(SignalingMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', IntField),
            ('call_ctx', IntField)]
            
        SignalingMessage.__init__(self, *args, **kwargs)
        
class HangupRequestAck(SignalingMessage):
    def __init__(self, *args, **kwargs):
        self.seq = [
            ('client_ctx', IntField),
            ('call_ctx', IntField)]
            
        SignalingMessage.__init__(self, *args, **kwargs)
        
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

    '\x00\x40': HangupRequest,
    '\x00\x41': HangupRequestAck,
    
    '\x00\xa0': ServerOverloaded
})

def keyof(_v):
    for k,v in MessageTypes.iteritems():
        if _v == v or isinstance(_v, v):
            return k

MessageTypes.keyof = keyof
