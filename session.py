#!/usr/bin/env python
# -*- coding: UTF-8 -*-


from __future__ import with_statement

__author__ = 'Tzury Bar Yochay'
__version__ = '0.1'
__license__ = 'GPLv3'

import time, Queue, struct, uuid, threading, sys, traceback

from twisted.internet import reactor
import dblayer, messages, config

from messages import *
from messagefields import *
from utils import Storage
from config import *
from decorators import printargs
from logger import log, cdr_logger
from pprint import PrettyPrinter

ppformat = PrettyPrinter().pformat
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
            
            # check if msg is ready to be packed
            if self.parser.eof(msg):
                msg = self.clients[client]
                if self.parser.valid(msg):
                    msg_type, buf = self.parser.body(self.clients[client])
                    ctr = MessageTypes[msg_type]
                    cm = CommMessage(client, ctr, buf)
                    self.queue.put(cm)
                else:
                    log.warning('unpackable (invalid) message %s' % repr(msg))
                
                # clean the packing pipeline for this client
                del self.clients[client]
            else:
                if client not in self.clients:
                    log.info('msg ignored')
                else:
                    log.info('no eof. waiting for more bytes')
        except:
            log.exception('exception')
            
    # receives the message and store it in the clients[client]
    def _recv(self, client, msg):
        try:
            # new client or new message
            if client not in self.clients:
                # check if message starts fine
                if self.parser.bof(msg):
                    # save the incoming msg
                    self.clients[client] = msg
                else:
                    log.info('unknown message from an unknown client (ignored)')
            else:
                # concatenate the incoming message to previous packets
                self.clients[client] = self.clients[client] + msg
        except:
            log.exception('exception')

'''a pool of all the listeners (tcp+udp) and their known clients'''
class ServersPool(Storage):
    def send_to(self, (host, port), data):
        if all((host, port, data)):
            listener = self.known_address((host, port))
            if listener:
                listener.server.send_to((host, port), data)
                return
            else:
                log.info("Unknown address %s:%s at ServerPool.send_to" % (host, port))
        else:
            log.info("Invalid args (%s,%s,%s) at ServerPool.send_to" % (host, port, repr(data)))
            
    def known_address(self, (host, port)):
        '''returns true if found a server which is connected to the client at the specified address'''
        for id, listener in self.iteritems():
            if listener.server.connected_to((host, port)):
                return listener
                
        return None
        
    def add(self, proto, server):
        self[uuid.uuid4().hex] = Storage(proto = proto, server=server)
        
class CtxTable(Storage):
    def add_client(self, (client_ctx, data)):
        with rlock():
            if len(self.keys()) < CONCURRENT_SESSIONS:
                self[client_ctx] = data
            
    def remove_client(self, client_ctx):
        with rlock():
            client = self.get(client_ctx)
            if client:
                # clear other's party call before removing this party
                self.terminate_call(client_ctx, False)
                del self[client_ctx]
        
    def clear_orphan_calls(self):
        for ctx in self.clients_ctx():
            call = self[ctx].current_call
            if call:
                other_ctx = (call.caller_ctx != ctx and call.caller_ctx) or call.callee_ctx
                
                if (# other party not exists
                    not self.get(other_ctx)
                    
                    # other party not in call
                    or not self[other_ctx].current_call
                    
                    #other party in call with someone else
                    or (self[other_ctx].current_call.callee_ctx != ctx
                        and self[other_ctx].current_call.caller_ctx != ctx)):
                            
                    log.warning('ORPHAN CALL REMOVED: CTX ', ctx)
                    self[ctx].current_call = None
        
    def mark_answer(self, client_ctx):
        call = self.client_call(client_ctx)
        if call:
            caller_ctx, callee_ctx = call.caller_ctx, call.callee_ctx
            if self.get(caller_ctx):
                self[caller_ctx].current_call.answer_time = time.time()
            if self.get(callee_ctx):
                self[callee_ctx].current_call.answer_time = time.time()
                
    def terminate_call(self, client_ctx, per_request=True):
        call = self.client_call(client_ctx)
        if call:
            log.info('hanging up call <%s>' % repr(call.ctx_id))
            call.end_time = time.time()
            cdr_logger.writeline(call)
            caller_ctx, callee_ctx = call.caller_ctx, call.callee_ctx
            if self.get(caller_ctx):
                self[caller_ctx].current_call = None
            if self.get(callee_ctx):
                self[callee_ctx].current_call = None
            
            ctx_table.pprint()
        else:
            log.info('no calls for client <%s>' % repr(client_ctx))
            
    def clients_ctx(self):
        '''all active clients (the keys)'''
        return self.iterkeys()
            
    def clients(self):
        '''all active clients (the values)'''
        return self.itervalues()
            
    def calls(self):
        '''all active calls'''
        return (self[client_ctx].current_call 
                for client_ctx in self.clients_ctx() 
                if self[client_ctx].current_call)
            
    def calls_ctx(self):
        '''all active calls contexts ids'''
        return (call.ctx_id for call in self.calls())
            
    def find_call(self, call_ctx):
        for call in self.calls():
            if call.ctx_id == call_ctx:
                return call
        return None
        
    def get_other_addr(self, client_ctx, call_ctx=config.EMPTY_CTX):
        call = None
        if call_ctx != config.EMPTY_CTX:
            call = self.find_call(call_ctx)
        else:
            call = self[client_ctx].current_call
            
        if call:
            return self.get_addr(
                (call.callee_ctx != client_ctx and call.callee_ctx)
                or call.caller_ctx)
        else:
            log.warning('Cannot find other party\'s context, '
                'client_ctx  <%s>, call_ctx <%s>. '
                'Might be removed at previous hangup request' 
                % (repr( client_ctx), repr(call_ctx)))
            return None
        
    def get_addr(self, client_ctx):
        '''return the last ip address registered for this client'''
        return client_ctx in self.clients_ctx() and self[client_ctx].addr
            
    def set_addr(self, client_ctx, (host, port)):
        '''register the last ip address for this client, used for replies'''
        if client_ctx in self.clients_ctx():
            self[client_ctx].addr = (host, port)
            
    def client_call(self, client_ctx):
        call_ctx = None
        if client_ctx in self.clients_ctx():
            call = self[client_ctx].current_call
            if not call:
                for call in self.calls():
                    if call.caller_ctx == client_ctx or call.callee_ctx == client_ctx:
                        return call
            return call
            
    def pprint(self):
        log.info('\nContextTable:\n%s>' % ppformat (self))
        
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
                current_call = None, 
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
            caller_ctx, callee_ctx, start_time, answer_time, end_time, codec, proto, ctx_id
        '''
        caller_ctx = request.msg.client_ctx.value
        callee_ctx = string_to_ctx(request.msg.calle_name.value)
        ctx_id =  string_to_ctx(caller_ctx, callee_ctx)
        ctx = Storage(
            caller_ctx = caller_ctx,
            callee_ctx = callee_ctx,
            start_time = time.time(),
            answer_time = 0,
            end_time = 0,
            #rtp_expire = 0,
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
                    
            log.info('%d old clients have been removed' % len(expired_clients))
            ctx_table.clear_orphan_calls()
            ctx_table.pprint()
            
        log.info('terminating thread: remove_old_clients')
    except:
        log.exception('exception')
    
def handle_inbound_queue():
    try:
        while thread_loop_active:
            try:
                req = inbound_messages.get(block=0)
                if req:
                    if req.msg_type != ClientRTP:
                        log.info('server received %s to %s' % (req.msg_type, repr(req.addr)))
                    else:
                        log.debug('server received %s to %s' % (req.msg_type, repr(req.addr)))
                        
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
            if reply and getattr(reply, 'msg') and getattr(reply, 'addr'):
                if reply.msg_type != ClientRTP:
                    log.info('server sends %s to %s' % (reply.msg_type, repr(reply.addr)))
                else:
                    log.debug('server sends %s to %s' % (reply.msg_type, repr(reply.addr)))
                    
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
        
        # login-request, otherwise context must exists in ctx_table
        if not ctx and msg_type != LoginRequest \
            or (ctx and ctx not in ctx_table.clients_ctx()):                
            log.warning(
                'filter is throwing away unknown '
                'msg_type/client_ctx: %s, %s, %s'
                %(repr(ctx), repr(msg_type), repr(msg)))
        else:
            
            addr = request.addr
            # client is now submitting from a new address
            if (request.client_ctx in ctx_table 
                # in ClientRTP the ctx represents teh invited party's ctx
                and msg_type != messages.ClientRTP
                and addr != ctx_table[request.client_ctx].addr):
                log.warning(msg_type)
                log.warning("Overriding old addr for client %s! old_addr %s, new_addr %s" 
                    % (request.client_ctx, ctx_table[request.client_ctx].addr, addr))
                
                ctx_table[request.client_ctx].addr = addr
            
            if msg_type == LoginRequest:
                _out = login_handler(request)
            elif msg_type == Logout:
                _out = logout_handler(request)
            elif msg_type == KeepAlive:
                _out = keep_alive_handler(request)
            elif isinstance(msg, SignalingMessage):
                _out = call_session_handler(request)
            elif msg_type == ClientRTP:
                _out = call_session_handler(request)
                
        if _out:
            for msg in _out:
                outbound_messages.put(msg)
            if ctx:
                touch_client(request.client_ctx, request.msg_type)
                
    except:
        log.exception('exception')
        
def touch_client(ctx, msg_type):
    try:
        if ctx in ctx_table:
            time_stamp = time.time()
            expire = time_stamp + CLIENT_EXPIRE
            ctx_table[ctx].last_keep_alive = time_stamp
            ctx_table[ctx].expire = expire
            '''
            if ctx_table[ctx].current_call and msg_type == ClientRTP:
                caller = ctx_table[ctx].current_call.caller_ctx
                callee = ctx_table[ctx].current_call.callee_ctx
                if ctx_table[caller].current_call:
                    ctx_table[caller].current_call.rtp_expire = expire
                if ctx_table[callee].current_call:
                    ctx_table[callee].current_call.rtp_expire = expire
            '''    
                
    except:
        log.exception('exception')        
        
def keep_alive_handler(request):
    try:
        expire = CLIENT_EXPIRE
        #reply with keep-alive-ack
        kaa = KeepAliveAck()
        
        kaa.set_values(client_ctx=request.client_ctx,
            expire = expire,
            refresh_contact_list = 0)
            
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
            
    def reply_login(ctx_id, ctx_data):
        try:
            '''returns a login reply'''
            lr = LoginReply()
            ip, port = ctx_data.addr
            codecs = sorted(Codecs.values())
            lr.set_values(client_ctx=ctx_id, client_public_ip=ip , 
                client_public_port=port, ctx_expire=ctx_table[ctx_id].expire - time.time(), 
                num_of_codecs=len(codecs), codec_list=''.join((c for c in codecs)))
            buf = lr.serialize()
            yield CommMessage(request.addr, LoginReply, buf)
        
        except:
            log.exception('exception')
        
    def deny_login():
        try:
            '''returns login-denied reply'''
            ld = ShortResponse()
            ld.set_values(client_ctx = 0, 
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
            return reply_login(ctx_id, ctx_data)
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
            
    @staticmethod
    def isretransmit(request):        
        if request.msg_type == ClientInvite:
            # case a: A invites B. B is already in call sesssion with A
            caller_ctx = request.msg.client_ctx.value
            callee_ctx = string_to_ctx(request.msg.calle_name.value)
            call = ctx_table[callee_ctx].current_call
            value = call and call.callee_ctx == callee_ctx and call.caller_ctx == caller_ctx
            if value:
                log.info("retransmission recognized", repr(request))
            return value
            
        return False
        
    def _handle_invite(self, request):
        try:
            caller_ctx = request.msg.client_ctx.value
            callee_ctx = string_to_ctx(request.msg.calle_name.value)
            
            # calle is not logged in
            if callee_ctx not in ctx_table:
                log.info('client_ctx ', callee_ctx, ' does not exist, rejecting invite.')
                return self._reject(config.Errors.CalleeNotFound, request)
                
            # calle is in another call session
            elif ctx_table[callee_ctx].current_call and not CallSession.isretransmit(request):
                if callee_ctx == caller_ctx:
                    log.info('client_ctx ', callee_ctx, ' is busy in another call, rejecting invite.')
                    return self._reject(config.Errors.CalleeUnavailable, request)

            #todo: add here `away-status` case handler
            matched_codecs = self._matched_codecs(request.msg.codec_list.value)
            log.debug('matched_codecs: %s' % matched_codecs)
            # caller codecs do not match with the server's
            if not matched_codecs:
                log.info('codecs mismatch -- rejecting invite')
                return self._reject(config.Errors.CodecMismatch, request)
            else:
                # create call ctx
                call_ctx_id, call_ctx = create_call_ctx(request)            
                # mark the caller as in another call session
                ctx_table[caller_ctx].current_call = call_ctx
                ctx_table[callee_ctx].current_call = call_ctx
                # send ServerForwardInvite to the calle
                return self._forward_invite(call_ctx, matched_codecs)
        except:
            log.exception('exception')
            
    def _forward_invite(self, call_ctx, matched_codecs):
        try:
            caller_ctx = call_ctx.caller_ctx
            callee_ctx = call_ctx.callee_ctx
            caller_name = ctx_table[caller_ctx].client_name        
            caller_ip, caller_port = ctx_table.get_addr(caller_ctx)
            codec_list = ''.join(matched_codecs)
            
            sfi = ServerForwardInvite()
            sfi.set_values(
                client_ctx = callee_ctx,
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
            yield CommMessage(ctx_table.get_addr(callee_ctx), ServerForwardInvite, sfi_buffer)
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
            msg, client_ctx, call_ctx = (
                request.msg, request.client_ctx, request.call_ctx)
            ctr = None
            other_addr = ctx_table.get_other_addr(client_ctx, call_ctx)
            call_ctx_data = ctx_table.find_call(call_ctx)
            if call_ctx_data and other_addr:
                if isinstance(msg, ClientInviteAck):                
                    return self._forward_invite_ack(msg, other_addr)
                elif isinstance(msg, ClientAnswer):
                    ctx_table.mark_answer(client_ctx)
                    return self._forward_client_answer(msg, other_addr)
                elif isinstance(msg, (HangupRequest, HangupRequestAck)):
                    return self._handle_hangup(request, other_addr)
            elif isinstance(msg, (HangupRequest)):
                return self._handle_hangup(request, other_addr)
            else:
                log.warning('_handle_signaling: call is out of context %s' % repr(call_ctx))
                ctx_table.pprint()
                
        except:
            log.exception('exception')

    def _handle_hangup(self, request, addr):
        buf = request.msg.serialize()
        
        if isinstance(request.msg, HangupRequestAck):
            ctx_table.terminate_call(request.client_ctx, True)
        
        yield CommMessage(addr, request.msg_type, buf)
        
            
    def _handle_rtp(self, request):
        try:
            call = ctx_table.find_call(request.call_ctx)
            if call:
                other_addr = ctx_table.get_other_addr(request.client_ctx, request.call_ctx)
                buf = request.msg.serialize()
                yield CommMessage(other_addr, ClientRTP, buf)
            else:
                log.warning('%s _handle_rtp: call is out of context %s' % (repr(self) ,repr(call)))
                ctx_table.pprint()
        except:
            log.exception('exception')
            
    def _reject(self, reason, request):
        try:
            log.info('server reject invite CTX:%s, Reason: %s' % (repr(request.client_ctx), repr(reason)))
            ctx = request.client_ctx
            sri = ServerRejectInvite()
            result = ShortField(0)
            result.unpack_from(reason)
            sri.set_values(client_ctx = ctx, result = result.value)            
            addr = ctx_table.get_addr(request.client_ctx)
            yield CommMessage(addr, ServerRejectInvite, sri.serialize())
        except:
            log.exception('exception')
        
    def _forward_invite_ack(self, cia, addr, call_type = CallTypes.ViaProxy):
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
            yield CommMessage(addr, ServerForwardRing,buf)
        except:
            log.exception('exception')
        
    def _forward_client_answer(self, msg, addr):
        try:
            # ?todo?: should copy call_ctx_data from the other party?
            buf = msg.serialize()
            yield CommMessage(addr, ClientAnswer,buf)
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
