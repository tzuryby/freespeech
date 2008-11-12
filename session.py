#!/usr/bin/env python

import time, Queue, struct
import dblayer, messages, config

from md5 import new as md5
from messageparser import Packer
from messages import *
from utils import Storage
from config import *
from decorators import printargs
from twisted.internet import reactor


class ServersPool(Storage):
    def send_to(self, (host, port), data):
        for id in self:
            if self[id].server.connected_to((host, port)):
                self[id].server.send_to((host, port), data)
                return
                
    def known_address(self, (host, port)):
        for id in self:
            if self[id].server.connected_to((host, port)):
                return True
                
    def add(self, id, proto, server):
        self[id] = Storage(proto = proto, server=server)
        
class CtxTable(Storage):
    def add_client(self, (ctx_id, ctx_data)):
        self[ctx_id] = ctx_data
        
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
    '''every server, onDataReceived call this function with the data'''
    msg_packer.pack((host, port), msg)
    
def create_client_context(comm_msg, status=ClientStatus.Unknown):
    '''creates the client context for each new logged in client        
    returns a tuple(ctx_id, client_ctx_data)
    client_ctx_data.keys() =>
        addr, status, expire, last_keep_alive, socket, proto, 
        socket_id, ctx_id, call_ctx, client_name
    '''
    ctx_id = comm_msg.client_ctx
    addr = comm_msg.addr
    if servers_pool.known_address(addr):
        now = time.time()
        ctx = Storage (addr=addr, status=status, expire=now + CLIENT_EXPIRE,
            last_keep_alive=now, ctx_id = ctx_id, call_ctx = None, 
            client_name = comm_msg.msg.username.value)
        return (ctx_id, ctx)
    else:
        return None

def create_call_ctx(request):
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
    
def remove_old_clients():
    while True:
        now = time.time()
        expired_clients = [client.ctx_id for client in ctx_table.clients() if client.expire < now]
        for ctx_id in expired_clients:
            print 'removing inactive client', repr(ctx_id)
            del ctx_table[ctx_id]
        time.sleep(CLIENT_EXPIRE)
            
'''             funcitonality not implemented                               '''
KeepAliveSession = SyncAddressBookSession = ChangeStatusSession = None
'''             end-of funcitonality not implemented                        '''

def handle_inbound_queue():
    while True:
        try:
            req = inbound_messages.get(block=0)
            if req:
                _filter(req)
        except Queue.Empty:
            time.sleep(0.010)
        
def handle_outbound_queue():
    while True:
        try:
            rep = outbound_messages.get(block=0)
            if rep and hasattr(rep, 'msg') and hasattr(rep, 'addr'):
                print 'server reply or forward a message to', rep.addr
                try:
                    data = rep.msg.serialize(True)
                    reactor.callFromThread(servers_pool.send_to,rep.addr, data)
                except:
                    print 'error while calling reactor.callFromThread at handle_outbound_queue'
        except Queue.Empty:
            time.sleep(0.010)
        
def _filter(request):
    _out = None
    msg = request.msg
    msg_type = request.msg_type
    ctx = hasattr(msg, 'client_ctx') and msg.client_ctx.value    
    if not ctx and msg_type != LoginRequest:
        _out = None        
    else:
        switch = {
            messages.LoginRequest: login_handler,
            messages.Logout: logout_handler,
            messages.KeepAlive: KeepAliveSession,
#            messages.ChangeStatus: ChangeStatusSession,
        }
        if msg_type in switch:
            _out = switch[msg_type](request)
        elif isinstance(msg, (SignalingMessage, ClientRTP)):
            _out = call_session_handler(request)
            
    if not _out:
        print 'filter is throwing away unknown msg_type: %s, %s'  %(repr(msg_type), repr(msg))
    else:
        outbound_messages.put(_out)
        if ctx:
            touch_client(request.client_ctx)        
        
def touch_client(ctx, time_stamp = time.time(), expire=None):
    if not expire:
        expire = time_stamp + CLIENT_EXPIRE
    
    print 'touch the glory of', repr(ctx)
    
    if ctx in ctx_table:
        ctx_table[ctx].last_keep_alive = time_stamp
        ctx_table[ctx].expire = expire

def login_handler(request):
    def verify_login(username, password):
        dbuser = users[unicode(username)]
        '''match supplied credentials with the database'''
        if dbuser and str(dbuser.password) == str(password):
            print 'login succseed'
            return dbuser
        else:
            return None
            
    def login_reply(ctx_id, ctx_data):
        '''creates login reply and put it in the outbound queue'''
        lr = LoginReply()
        ip, port = ctx_data.addr
        codecs = sorted(Codecs.values())
        lr.set_values(client_ctx=ctx_id, client_public_ip=ip , 
            client_public_port=port, ctx_expire=ctx_table[ctx_id].expire - time.time(), 
            num_of_codecs=len(codecs), codec_list=''.join((c for c in codecs)))
        buf = lr.serialize(False)
        print 'login reply', repr(buf)
        return CommMessage(request.addr, LoginReply, buf)
        
    def deny_login():
        '''creates login-denied reply and put it in the outbound queue'''
        ld = ShortResponse()
        ld.set_values(
            client_ctx = ('\x00 '*16).split(),
            result = struct.unpack('!h', Errors.LoginFailure))
        buf = ld.serialize(False)
        print 'login error'    
        return CommMessage(request.addr, ShortResponse, buf)
        
    username, password = request.msg.username.value, request.msg.password.value
    dbuser = verify_login(username, password)
    if dbuser:
        #creates new client context and register it
        ctx_id, ctx_data = create_client_context(request, status=dbuser.login_status)    
        ctx_table.add_client((ctx_id, ctx_data))
        return login_reply(ctx_id, ctx_data)
    else:
        return deny_login(request)

def logout_handler(request):
    del ctx_table[request.client_ctx]
    
class CallSession(object):
    '''Utility class handles all requests/responses regarding a call session'''
    def handle(self, request):
        if request.msg_type == ClientInvite:
            return self._handle_invite(request)
        elif isinstance(request.msg, SignalingMessage):
            return self._handle_signaling(request)
        elif isinstance(request.msg, ClientRTP):
            return self._handle_rtp(request)
            
    def _handle_invite(self, request):
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
        print 'matched_codecs:', matched_codecs
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

    def _forward_invite(self, call_ctx, matched_codecs):
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
        
        sfi_buffer = sfi.serialize(False)
        return CommMessage(ctx_table.get_addr(calle_ctx), ServerForwardInvite, sfi_buffer)
        
    def _matched_codecs(self, client_codecs):
        '''returns either `0` or a list of matched codecs between the client and the server'''
        server_codecs = config.Codecs.values()
        # inefficient algorithm
        matched_codecs = [codec for codec in client_codecs if codec in server_codecs]
        return len(matched_codecs) and matched_codecs
            
    def _handle_signaling(self, request):
        ctr, msg, call_ctx = None, request.msg, request.call_ctx
        
        if call_ctx in ctx_table.calls_ctx():
            calle_addr = request.addr
            call_ctx = ctx_table.find_call(call_ctx)
            if call_ctx:
                caller_addr = ctx_table.get_addr(call_ctx.caller_ctx)                
                if isinstance(msg, ClientInviteAck):                
                    buf = self._forward_invite_ack(msg)
                    ctr = ServerForwardRing
                elif isinstance(msg, ClientAnswer):
                    # ClientAnswer is forwarded as is
                    buf = msg.serialize(False)
                    ctr = ClientAnswer                
        else:
            print '_handle_signaling: call is out of context', repr(call_ctx)
            
        return ctr and CommMessage(caller_addr, ctr, buf)
        
    def _handle_rtp(self, request):
        call_ctx = ctx_table.find_call(request.call_ctx)
        if call_ctx:
            forward_to = (call_ctx.caller_ctx == request.client_ctx and call_ctx.calle_ctx) \
                or request.client_ctx                
            request.addr = ctx_table.get_addr(forward_to)
            return request
        else:    
            print self, '_handle_rtp: call is out of context', repr(call_ctx)
            
    def _reject(self, reason, request):
        reject = ServerRejectInvite(client_ctx=request.client_ctx, reason=reason)
        return CommMessage(addr, ServerRejectInvite, reject.serialize(False))
        
    def _forward_invite_ack(self, cia, call_type = CallTypes.ViaProxy):
        sfr = ServerForwardRing()
        sfr.set_values(
            client_ctx = cia.client_ctx.value,
            call_ctx = cia.call_ctx.value,
            client_status = cia.client_status.value,
            call_type = call_type,
            client_public_ip = cia.client_public_ip.value,
            client_public_port = cia.client_public_port.value)
        buf = sfr.serialize(False)
        return buf
        
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