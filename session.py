#!/usr/bin/env python

'''
'''

import time, Queue, struct
import dblayer, messages, config

from md5 import new as md5
from serverfactory import serve
from messageparser import *
from messages import *
from utils import Storage
from config import *
from decorator import printargs


'''
    the first time a client is connected:
        it sends a login-request
        if a login request succeed as a result the system creates client_ctx
        this context id is registered at the ctx_table along with the client's address
        at every message the system saves the last addr in order to reply to it.
            (in udp it mihgt changed during active session)
        every keep-alive the system stamps the client
        when a client sends invote to another client
            the caller's call_ctx is stamped by a new call_ctx
            when the calle answer the calle is stampped by the same data.
            
        to do: add log mechanism for the calls (ie CDR)
        
    for each client I save the addr, and the server_id that is the tcp/udp listener 
    which is connected to. when replying to a client simply call server[server_id].send_to(addr, msg)
'''

# client_ctx: { call_ctx: {} }
class CtxTable(Storage):
    def add_client(self, (ctx_id, ctx_data)):
        self[ctx_id] = ctx_data
        
    def add_call(self, client_ctx, call_ctx):
        if client_ctx in self:
            self[client_ctx].call_ctx = call_ctx
            
    def clients(self):
        '''all active clients'''
        return (ctx for ctx in self)
            
    def touch_client(self, client_ctx):
        if client_ctx in self:
            self[client_ctx].last_keep_alive = time.time()
            
    def calls(self):
        '''all active calls'''
        return (self[ctx].call_ctx for ctx in self if self[ctx].call_ctx)
            
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
            
ctx_table = CtxTable()

# Packer.pack will pack each request into this queue
inbound_messages = Queue.Queue()

# replies from server to client
outbound_messages = Queue.Queue()

# packs any incoming message and put it in the inbound_messages queue
msg_packer = Packer(inbound_messages)
msg_parser = Parser()
users = dblayer.Users

def map_socket(addr, socket, proto, socket_id):
    ''' callback for 'register' trigger at the server
    map a client to a socekt at one of the available listeners'''
    sockets_map[addr] = (socket, proto, socket_id)
    
def recv_msg(addr, msg):
    ''' callback for 'handler' trigger at the server '''
    msg_packer.pack(addr, msg)
    
def create_client_context(comm_msg, status=ClientStatus.Unknown):
    '''creates the client context for each new logged in client        
    returns a tuple(ctx_id, client_ctx_data)
    client_ctx_data.keys() =>
        addr, status, expire, last_keep_alive, socket, proto, socket_id, ctx_id, call_ctx, client_name
    '''
    ctx_id = comm_msg.client_ctx
    addr = comm_msg.addr
    if addr in sockets_map:
        socket, proto, socket_id = sockets_map[addr]
        now = time.time()
        ctx = Storage (addr=addr, status=status, expire=now + CLIENT_EXPIRE, 
            last_keep_alive=now, socket=socket, proto=proto, socket_id=socket_id, ctx_id = ctx_id, call_ctx = None, 
            client_name = comm_msg.msg.username.value)
            
        return ctx_id, ctx
        
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
        proto = sockets_map[request.addr][1],
        ctx_id = ctx_id
    )
    
    return ctx_id, ctx
    
def remove_old_clients():
    while True:
        now = time.time()
        expired_clients = [ctx for ctx in clients_ctx if clients_ctx[ctx].expire < now]
        for ctx in expired_clients:
            print 'removing inactive client', repr(ctx)
            del clients_ctx[ctx]
        time.sleep(CLIENT_EXPIRE)

def request_queue():
    while True:
        try:
            yield inbound_messages.get(block=0)
        except Queue.Empty:
            yield None
            
def replies_queue():
    while True:
        try:
            yield outbound_messages.get(block=0)
        except Queue.Empty:
            yield None
    
def _handle_request(request):
    switch = {
        messages.Logout: LogoutSession,
        messages.KeepAlive: KeepAliveSession,
        messages.ChangeStatus: ChangeStatusSession
    }
    msg_type = request.msg_type
    msg_type in switch and touch_client(request.client_ctx)
    if msg_type in switch:
        switch[msg_type](request.msg)
    else:
        call_session.handle(request)
    
class LogoutSession(object):
    def __init__(self, request):
        pass
        
KeepAliveSession = SyncAddressBookSession = \
    ChangeStatusSession = CallSession = LogoutSession

def _filter(msg):
    #msg_type, ctx = msg.msg_type, msg.client_ctx
    msg_type = msg.msg_type
    # system will handle only from known clients or login requests
    if msg_type == LoginRequest:
        LoginSession(msg)
        return
        
    ctx = hasattr(msg.msg, 'client_ctx') and msg.msg.client_ctx.value
    if ctx and ctx in clients_ctx:
        _handle_request(msg)
    else:
        print 'throwing away unknown message', msg
        
def handle_requests():
    while True:
        for req in request_queue():
            if req:
                _filter(req)
        time.sleep(0.1)
        
        
def send_test():
    while True:
        for addr in sockets_map:
            sockets_map.send(addr, 'your addr is:' + str(addr))
            
        time.sleep(10)
            
def handle_replies():
    while True:
        for rep in replies_queue():
            if rep:
                print 'server sends a reply or forward a message'
                sockets_map.send(rep.addr, rep.msg.serialize())
        time.sleep(0.1)
                
def touch_client(ctx, time_stamp = time.time(), expire=CLIENT_EXPIRE):
    if ctx in clients_ctx:
        clients_ctx[ctx].last_keep_alive = time_stamp
        clients_ctx[ctx].expire = expire        
    

class LoginSession(object):
    '''Manages the login session
    LoginRequest -> Verify Login -> Client_CTX Creation -> Login Reply
    '''
    def __init__(self, request):
        print 'initializing login session'
        if request.msg_type == LoginRequest:
            self.login_request = request
            if self.verify_login():
                self.create_client_ctx()
                self.reply_login()
            else:
                self.deny_login()
                
    def verify_login(self):
        '''match supplied credentials with the database'''
        username = self.login_request.msg.username
        password = self.login_request.msg.password        
        dbuser = users[unicode(username)]
        if dbuser and str(dbuser.password) == str(password):
            self.dbuser = dbuser
            print 'login succseed'
            return True
        else:
            return False
            
    def create_client_ctx(self):
        '''creates new client context and register it'''
        ctx = create_client_context(self.login_request, status=self.dbuser.login_status)
        self.ctx_id, self.ctx_data = ctx
        clients_ctx.register(ctx)
            
    def reply_login(self):
        '''creates login reply and put it in the outbound queue'''
        lr = LoginReply()
        ip, port = self.ctx_data.addr
        codecs = Codecs.values()
        lr.set_values(client_ctx=self.ctx_id, 
            client_public_ip=ip , client_public_port=port, 
            ctx_expire=clients_ctx[self.ctx_id].expire, 
            num_of_codecs=len(codecs), 
            codec_list=''.join((c for c in codecs)))
        buf = lr.get_buffer()
        print 'login reply', repr(buf)
        cm = CommMessage(self.login_request.addr, LoginReply, buf)
        outbound_messages.put(cm)
        
    def deny_login(self):
        '''creates login-denied reply and put it in the outbound queue'''
        ld = ShortResponse()
        ld.set_values(
            client_ctx = ('\x00 '*16).split(),
            result = struct.unpack('!h', Errors.LoginFailure))
        buf = ld.get_buffer()
        cm = CommMessage(self.login_request.addr, ShortResponse, buf)
        outbound_messages.put(cm)
        print 'login error'

class CallSession(object):
    '''Utility class handles all requests/responses regarding a call session
    _filter should only call 'handle' method
    '''
    def handle(self, request):
        if request.msg_type == ClientInvite:
            self._handle_invite(request)
        elif isinstance(request.msg, SignalingMessage):
            self._handle_signaling(request)
        elif request.msg_type == ServerRTPRelay:
            self._handle_rtp(request)
            
    def _handle_invite(self, request):
        caller_ctx = request.msg.client_ctx.value
        calle_ctx = string_to_ctx(request.msg.calle_name.value)
        
        # calle is not logged in
        if calle_ctx not in clients_ctx:
            self._reject(config.Errors.CalleeNotFound, request)
            
        # calle is in another call session
        elif clients_ctx[calle_ctx].call_ctx:
            self._reject(config.Errors.CalleeUnavailable, request)
            
        #todo: add here `away-status` case handler
        matched_codecs = self._matched_codecs(request.msg.codec_list.value)
        print 'matched_codecs:', matched_codecs
        # caller codecs do not match with the server's
        if not matched_codecs:
            self._reject(config.Errors.CodecMismatch, request)
        else:
            # create call ctx
            call_ctx = self._create_call_ctx(request)
            
            # mark the caller as in another call session
            self._set_client_busy(caller_ctx, call_ctx)
            
            # send ServerForwardInvite to the calle
            self._forward_invite(call_ctx, matched_codecs)
            
    def _create_call_ctx(self, request):
        call_ctx_id, call_ctx = create_call_ctx(request)
        return call_ctx
        
    def _forward_invite(self, call_ctx, matched_codecs):
        caller_ctx = call_ctx.caller_ctx
        calle_ctx = call_ctx.calle_ctx
        caller_name = clients_ctx[caller_ctx].client_name        
        caller_ip, caller_port = clients_ctx.get_addr(caller_ctx)
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
        print '*'*40, '\n'*3
        print '_forward_invite->locals()', locals()
        print '*'*40, '\n'*3
        print 'current clients:', clients_ctx
        print '*'*40, '\n'*3
        print 'active sockets:', sockets_map
        print '*'*40, '\n'*3
        #sfi_buffer = sfi.get_buffer()
        #print 'ServerForwardInvite:', repr(sfi_buffer)
        
        print repr(calle_ctx), clients_ctx[calle_ctx].client_name, clients_ctx[calle_ctx].addr
        clients_ctx[calle_ctx].socket.send(sfi.serialize())
        
        #self._out(clients_ctx.get_addr(calle_ctx), ServerForwardInvite, sfi_buffer)
        
    def _matched_codecs(self, client_codecs):
        '''returns either `0` or a list of matched codecs between the client and the server'''
        server_codecs = config.Codecs.values()
        # inefficient algorithm
        matched_codecs = [codec for codec in client_codecs if codec in server_codecs]
        return len(matched_codecs) and matched_codecs
            
    def _handle_signaling(self, request):
        if _call_in_ctx(request.msg.call_ctx):
            # use: ClientsCtx.get_addr in order to retrive the `other` client addr
            pass
            
    def _handle_rtp(self, request):
        if _call_in_ctx(request.msg.call_ctx):
            # do your duty
            pass
        
    def _call_in_ctx(self, call_ctx):
        return call_ctx in calls_ctx
        
    def _reject(self, reason, request):
        reject = ServerRejectInvite(client_ctx=request.msg.client_ctx, reason=reason)
        self._out(addr, ServerRejectInvite, reject.get_buffer())
        
    def _out(self, addr, ctr, buf):
        '''put in the outbound queue a new CommMessage built using the supplied parameters'''
        cm = CommMessage(addr, ctr, buf)
        outbound_messages.put(cm)
        
    def _set_client_busy(self, client_ctx, call_ctx):
        clients_ctx[client_ctx].call_ctx = call_ctx

call_session = CallSession()
