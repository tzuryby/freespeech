#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import with_statement

import time, Queue, struct, uuid 
import threading, sys, traceback

import dblayer, messages, config

from md5 import new as md5
from messages import *
from utils import Storage
from config import *
from decorators import printargs
from logger import log
from twisted.internet import reactor
from logger import log

rlock = lambda: threading.RLock()

thread_loop_active = True

class Packer(object):
    '''Packs parts of message into a message object and enqueue it'''
    def __init__(self, queue):
        self.clients = dict()
        self.queue = queue
        self.parser = Parser()
        
    def pack(self, client, msg):
        try:
            self._recv(client, msg)
            if self.parser.eof(msg):
                # get the whole message
                msg = self.clients[client]
                if self.parser.valid(msg):
                    msg_type, buf = self.parser.body(self.clients[client])
                    ctr = MessageTypes[msg_type]
                    cm = CommMessage(client, ctr, buf)
                    self.queue.put(cm)                    
                else:
                    log.warning('Packer.pack() >>> not a valid message %s' % msg)
                
                del self.clients[client]
            else:
                log.warning('Packer.pack() >>> eof not found, waiting for more bytes')
        except:
            log.exception('exception')
            
    # receives the message and store it in the clients[client]
    def _recv(self, client, msg):
        try:
            # new client or new message
            if (client not in self.clients and self.parser.bof(msg)):
                self.clients[client] = msg
            else:
                self.clients[client] = self.clients[client] + msg
        except:
            log.exception('exception')

'''a pool of all the listeners (tcp+udp) and thier known clients'''
class ServersPool(Storage):
    def send_to(self, (host, port), data):
        for id, listener in self.iteritems():
            if listener.server.connected_to((host, port)):
                listener.server.send_to((host, port), data)
                return
                
    def known_address(self, (host, port)):
        '''returns true if found a server which is connected to the client at the specified address'''
        for id, listener in self.iteritems():
            if listener.server.connected_to((host, port)):
                return True
                
    def add(self, proto, server):
        self[uuid.uuid4().hex] = Storage(proto = proto, server=server)
        
class CtxTable(Storage):
    def add_client(self, (ctx_id, ctx_data)):
        with rlock():
            self[ctx_id] = ctx_data
            
    def remove_client(self, ctx_id):
        '''todo: check if need to clean the the call record at the other party'''
        with rlock():
            del self[ctx_id]
        
    def clients_ctx(self):
        '''all active clients (the keys)'''
        return self.keys()
            
    def clients(self):
        '''all active clients (the values)'''
        return self.values()
            
    def calls(self):
        '''all active calls'''
        return (self[ctx].call_ctx for ctx in self if self[ctx].call_ctx)
            
    def calls_ctx(self):
        '''all active calls contexts ids'''
        return (call.ctx_id for call in self.calls())
            
    def find_call(self, call_ctx):
        for call in self.calls():
            if call.ctx_id == call_ctx:
                return call
                
    def get_addr(self, client_ctx):
        '''return the last ip address registered for this client'''
        return client_ctx in self and self[client_ctx].addr
            
    def set_addr(self, client_ctx, (host, port)):
        '''register the last ip address for this client, used for replies'''
        if client_ctx in self:
            self[client_ctx].addr = (host, port)
            
    def client_call(self, client_ctx):
        return client_ctx in self and self[client_ctx].call_ctx
            
    def keep_alives(self):
        '''generator of tuples (client_ctx_id, last_keep_alive)'''
        return ((ctx, self[ctx].last_keep_alive) for ctx in self)
            
    def names(self):
        '''all connected clients user names'''
        return (self[ctx].client_name for ctx in self)
            
    def clients_status(self):
        '''all connected clients user names and their status (name, status)'''
        return ((self[ctx].client_name, self[ctx].status) for ctx in self)
            
def recv_msg(caller, (host, port), msg):
    try:
        '''every server, onDataReceived call this function with the data'''
        msg_packer.pack((host, port), msg)
    except:
        log.exception('exception')
            
def create_client_context(comm_msg, status=ClientStatus.Unknown):
    try:
        '''creates the client context for each new logged in client        
        returns a tuple(ctx_id, client_ctx_data)
        client_ctx_data.keys() =>
          addr, status, expire, last_keep_alive, ctx_id, call_ctx, client_name
        '''
        ctx_id = comm_msg.client_ctx
        addr = comm_msg.addr
        if servers_pool.known_address(addr):
            now = time.time()
            ctx = Storage (
                addr=addr, 
                status=status, 
                expire=now + CLIENT_EXPIRE,
                last_keep_alive=now, 
                ctx_id = ctx_id, 
                call_ctx = None, 
                client_name = comm_msg.msg.username.value
            )
            return (ctx_id, ctx)
        else:
            return None
    except:
        log.exception('exception')
            
def create_call_ctx(request):
    try:
        '''creates the call context for each valid invite
        returns a tuple(ctx_id, call_ctx_data)
        call_ctx_data.keys() =>
            caller_ctx, calle_ctx, start_time, answer_time, end_time, codec, proto, ctx_id
        '''
        caller_ctx = request.msg.client_ctx.value
        calle_ctx = string_to_ctx(request.msg.calle_name.value)
        ctx_id =  string_to_ctx(caller_ctx, calle_ctx)
        ctx = Storage(
            caller_ctx = caller_ctx,
            calle_ctx = calle_ctx,
            start_time = time.time(),
            answer_time = 0,
            end_time = 0,
            codec = None,
            ctx_id = ctx_id
        )
        return (ctx_id, ctx)
    except:
        log.exception('exception')
    
def remove_old_clients():
    try:
        while thread_loop_active:
            now = time.time()
            expired_clients = [client.ctx_id for client in ctx_table.clients() if client.expire < now]
            
            for ctx_id in expired_clients:
                log.info('removing inactive client ' + repr(ctx_id))
                ctx_table.remove_client(ctx_id)
                    
            for i in xrange(CLIENT_EXPIRE):
                if thread_loop_active:
                    time.sleep(1)
                else:
                    break
                
        log.info('terminating thread: remove_old_clients')
    except:
        log.exception('exception')
    
def handle_inbound_queue():
    try:
        while thread_loop_active:
            try:
                req = inbound_messages.get(block=0)
                if req:
                    log.debug('server received %s to %s [%s]' % (
                        req.msg_type, repr(req.addr), repr(req.body)))
                    _filter(req)
            except Queue.Empty:
                time.sleep(0.010)
                
        log.info('terminating thread: handle_inbound_queue')
    except:
        log.exception('exception')
        
def handle_outbound_queue():
    while thread_loop_active:
        try:
            reply = outbound_messages.get(block=0)
            if reply and hasattr(reply, 'msg') and hasattr(reply, 'addr'):
                log.debug('server sends %s to %s [%s]' % (
                    reply.msg_type, repr(reply.addr), repr(reply.body)))
                try:
                    data = reply.msg.pack()
                    reactor.callFromThread(servers_pool.send_to,reply.addr, data)
                except Exception, inst:
                    log.exception('exception')
                    
        except Queue.Empty:
            time.sleep(0.010)
        except:
            log.exception('exception')
            
    log.info('terminating thread: handle_outbound_queue')
    
def _filter(request):
    try:
        _out = None
        msg = request.msg
        msg_type = request.msg_type
        ctx = getattr(msg, 'client_ctx', None) and msg.client_ctx.value
        
        if not ctx and msg_type != LoginRequest \
            or (ctx and ctx not in ctx_table.clients_ctx()):
                
            log.warning(
                'filter is throwing away unknown '
                'msg_type/client_ctx: %s, %s, %s'
                %(repr(ctx), repr(msg_type), repr(msg)))                
        else:
            switch = {
                LoginRequest: login_handler,
                Logout: logout_handler,
                KeepAlive: keep_alive_handler 
            }
                
            if msg_type in switch.keys():
                _out = switch[msg_type](request)
                
            elif isinstance(msg, (SignalingMessage, ClientRTP)):
                _out = call_session_handler(request)
                
        if _out:
            for msg in _out:
                outbound_messages.put(msg)
            if ctx:
                touch_client(request.client_ctx)
    except:
        log.exception('exception')
        
def touch_client(ctx):
    try:
        if ctx in ctx_table:
            time_stamp = time.time()
            expire = time_stamp + CLIENT_EXPIRE
            ctx_table[ctx].last_keep_alive = time_stamp
            ctx_table[ctx].expire = expire
            
    except:
        log.exception('exception')        
        
def keep_alive_handler(request):
    try:
        expire = CLIENT_EXPIRE
        #reply with keep-alive-ack
        kaa = KeepAliveAck()
        
        kaa.set_values(
            client_ctx=request.client_ctx,
            expire = expire,
            refresh_contact_list = 0
        )
        
        yield CommMessage(request.addr, KeepAliveAck, kaa.serialize())
    except:
        log.exception('exception')
    
def login_handler(request):
    def verify_login(username, password):
        try:
            dbuser = users.get(unicode(username))
            '''match supplied credentials with the database'''
            if dbuser and str(dbuser.password) == str(password):
                log.info('login succseed')
                return dbuser
            else:
                log.info('login failed')
                return None
        except:
            log.exception('exception')

            
    def login_reply(ctx_id, ctx_data):
        try:
            '''returns a login reply'''
            lr = LoginReply()
            ip, port = ctx_data.addr
            codecs = sorted(Codecs.values())
            lr.set_values(client_ctx=ctx_id, client_public_ip=ip , 
                client_public_port=port, ctx_expire=ctx_table[ctx_id].expire - time.time(), 
                num_of_codecs=len(codecs), codec_list=''.join((c for c in codecs)))
            buf = lr.serialize()
            log.debug('login reply')
            yield CommMessage(request.addr, LoginReply, buf)
        except:
            log.exception('exception')
        
    def deny_login():
        try:
            '''returns login-denied reply'''
            ld = ShortResponse()
            ld.set_values(
                client_ctx = ('\x00 '*16).split(),
                result = struct.unpack('!h', Errors.LoginFailure))
            buf = ld.serialize()
            log.info('login error')
            yield CommMessage(request.addr, ShortResponse, buf)
        except:
            log.exception('exception')
        
    try:
        username, password = request.msg.username.value, request.msg.password.value
        dbuser = verify_login(username, password)
        if dbuser:
            #creates new client context and register it
            ctx_id, ctx_data = create_client_context(request, status=dbuser.login_status)    
            ctx_table.add_client((ctx_id, ctx_data))
            return login_reply(ctx_id, ctx_data)
        else:
            return deny_login()
    except:
        log.exception('exception')
        
def logout_handler(request):
    try:
        with rlock():
            ctx_table.remove_client(request.client_ctx)
    except:
        log.exception('exception')

class CallSession(object):
    '''Utility class handles all requests/responses regarding a call session'''
    def handle(self, request):
        try:
            if request.msg_type == ClientInvite:
                return self._handle_invite(request)
            elif isinstance(request.msg, SignalingMessage):
                return self._handle_signaling(request)
            elif isinstance(request.msg, ClientRTP):
                return self._handle_rtp(request)
        except:
            log.exception('exception')
            
    def _handle_invite(self, request):
        try:
            caller_ctx = request.msg.client_ctx.value
            calle_ctx = string_to_ctx(request.msg.calle_name.value)
            
            # calle is not logged in
            if calle_ctx not in ctx_table:
                return self._reject(config.Errors.CalleeNotFound, request)
                
            # calle is in another call session
            elif ctx_table[calle_ctx].call_ctx:
                return self._reject(config.Errors.CalleeUnavailable, request)
                
            #todo: add here `away-status` case handler
            matched_codecs = self._matched_codecs(request.msg.codec_list.value)
            log.debug('matched_codecs: %s' % matched_codecs)
            # caller codecs do not match with the server's
            if not matched_codecs:
                return self._reject(config.Errors.CodecMismatch, request)
            else:
                # create call ctx
                call_ctx_id, call_ctx = create_call_ctx(request)            
                # mark the caller as in another call session
                ctx_table[caller_ctx].call_ctx = call_ctx
                # send ServerForwardInvite to the calle
                return self._forward_invite(call_ctx, matched_codecs)
        except:
            log.exception('exception')
            
    def _forward_invite(self, call_ctx, matched_codecs):
        try:
            caller_ctx = call_ctx.caller_ctx
            calle_ctx = call_ctx.calle_ctx
            caller_name = ctx_table[caller_ctx].client_name        
            caller_ip, caller_port = ctx_table.get_addr(caller_ctx)
            codec_list = ''.join(matched_codecs)
            
            sfi = ServerForwardInvite()
            sfi.set_values(
                client_ctx = calle_ctx,
                call_ctx = call_ctx.ctx_id,
                call_type = config.CallTypes.ViaProxy,
                client_name_length = len(caller_name),
                client_name = caller_name,
                client_public_ip = caller_ip,
                client_public_port = caller_port,
                num_of_codecs = len(matched_codecs),
                codec_list = codec_list
            )
            
            sfi_buffer = sfi.serialize()
            yield CommMessage(ctx_table.get_addr(calle_ctx), ServerForwardInvite, sfi_buffer)
        except:
            log.exception('exception')
        
    def _matched_codecs(self, client_codecs):
        try:
            '''returns either `0` or a list of matched codecs between the client and the server'''
            server_codecs = config.Codecs.values()
            # inefficient algorithm
            matched_codecs = [codec for codec in client_codecs if codec in server_codecs]
            return len(matched_codecs) and matched_codecs
        except:
            log.exception('exception')
            
    def _handle_signaling(self, request):
        try:
            ctr, msg, client_ctx, call_ctx = \
            None, request.msg, request.client_ctx, request.call_ctx
            
            if call_ctx in ctx_table.calls_ctx():
                calle_addr = request.addr
                call_ctx_data = ctx_table.find_call(call_ctx)
                if call_ctx_data:
                    caller_addr = ctx_table.get_addr(call_ctx_data.caller_ctx)                
                    if isinstance(msg, ClientInviteAck):                
                        return self._forward_invite_ack(msg, caller_addr)
                    elif isinstance(msg, ClientAnswer):
                        return self._forward_client_answer(msg, caller_addr)
                    elif isinstance(msg, (HangupRequest, HangupRequestAck)):
                        return self._handle_hangup(request, client_ctx, call_ctx_data)
            else:
                log.warning('_handle_signaling: call is out of context %s' % repr(call_ctx))
                
        except:
            log.exception('exception')

    def _handle_hangup(self, request, client_ctx, call_ctx_data):
        forward_to = (call_ctx_data.caller_ctx == client_ctx 
            and call_ctx_data.calle_ctx) or client_ctx
        addr = ctx_table.get_addr(forward_to)
        buf = request.msg.serialize()
        
        if request.msg_type in (HangupRequest, HangupRequestAck, ):
            yield CommMessage(addr, request.msg_type, buf)
            
    def _handle_rtp(self, request):
        try:
            call_ctx = ctx_table.find_call(request.call_ctx)
            if call_ctx:
                # get the other party client_ctx
                forward_to = (call_ctx.caller_ctx == request.client_ctx 
                    and call_ctx.calle_ctx) or request.client_ctx
                request.addr = ctx_table.get_addr(forward_to)
                yield request
            else:    
                log.warning('%s _handle_rtp: call is out of context %s' % (repr(self) ,repr(call_ctx)))
        except:
            log.exception('exception')
            
    def _reject(self, reason, request):
        try:
            log.info('server reject invite CTX:%s, Reason: %s' % (repr(request.client_ctx), repr(reason)))
            #reject = ServerRejectInvite(client_ctx=request.client_ctx, result=reason)
            ctx = request.client_ctx
            sri = ServerRejectInvite()
            result = ShortField(0)
            result.unpack_from(reason)
            sri.set_values(client_ctx = ctx, result = result.value)            
            addr = ctx_table.get_addr(request.client_ctx)
            yield CommMessage(addr, ServerRejectInvite, sri.serialize())
        except:
            log.exception('exception')
        
    def _forward_invite_ack(self, cia, caller_addr, call_type = CallTypes.ViaProxy):
        try:
            sfr = ServerForwardRing()
            sfr.set_values(
                client_ctx = cia.client_ctx.value,
                call_ctx = cia.call_ctx.value,
                client_status = cia.client_status.value,
                call_type = call_type,
                client_public_ip = cia.client_public_ip.value,
                client_public_port = cia.client_public_port.value)
            buf = sfr.serialize()
            yield CommMessage(caller_addr, ServerForwardRing,buf)
        except:
            log.exception('exception')
        
    def _forward_client_answer(self, msg, caller_addr):
        try:
            buf = msg.serialize()
            yield CommMessage(caller_addr, ClientAnswer,buf)
        except:
            log.exception('exception')
        
#########################################
# all module Singletons
#########################################

# main table which I store all the contexts in
ctx_table = CtxTable()

# a reference for all the server launched by the reactor
servers_pool = ServersPool()

# Packer.pack will pack each request into this queue
inbound_messages = Queue.Queue()

# replies from server to client
outbound_messages = Queue.Queue()

# packs any incoming message and put it in the inbound_messages queue
msg_packer = Packer(inbound_messages)

users = dblayer.Users
    
#_call_session = CallSession()
call_session_handler = CallSession().handle
