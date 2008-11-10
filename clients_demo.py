import sys
import socket
import struct
import time
import Queue

from messageparser import Packer, Parser
from threading import Thread
from messages import *
from config import Codecs, ClientStatus
from decorators import printargs

class TcpClient(Thread):
    def __init__(self, (host, port), recv_callback = None):
        Thread.__init__(self)
        #self.host, self.port= host, port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((host, port))
        self.recv_callback = recv_callback

    def send(self, msg):
        self.socket.send(msg)
        
    def run(self):
        data = '^#$_@!#$'
        while data:
            data = self.socket.recv(1024*4)
            print 'recieved:', repr(data)
            self.recv_callback and self.recv_callback(data)
            
    def close(self):
        self.socket.close()
            
class SnoipClient(object):
    
    def __init__(self, (host, port)):
        self.client = TcpClient(host, port)
        self.client.recv_callback = self.recv
        self.parser = Parser()
        self.client.start()
        
    def recv(self, data):
        msg_type, buf = self.parser.body(data)
        print 'msg_type', msg_type
        if msg_type in MessageTypes:
            msg = MessageTypes[msg_type](buf=buf)
            if isinstance(msg, LoginReply):
                self.login_reply(msg)
            elif isinstance(msg, ServerForwardInvite):
                self.client_invite_ack(msg)
                
    def login_request(self, username, password):
        data = create_login_msg(username, password)
        self._send(data)
        
    def login_reply(self, msg):
        self.client_ctx = msg.client_ctx.value
        
    def invite(self, username):
        data = create_invite(self.client_ctx, username)
        self._send(data)
        
    def ack_invite(self, sfi):
        data = client_invite_ack(sfi)
        self._send(data)
        
    def answer(self):
        pass
        
    def _send(self, data):
        self.client.send(data)
        
def create_login_msg(username, password='0'*20):
    header = '\xab\xcd'
    trailer = '\xdc\xba'
    msg_type = '\x00\x01'
    
    username_length = struct.pack('!b', len(username))
    username = struct.pack('!%dc' % len(username), *(username))
    password = struct.pack('!20c',*(password))
    ip = struct.pack('!16b', *(0 for i in xrange(16)))
    port = struct.pack('!i', 0)
    msg_length = struct.pack('!h',  sum(map(lambda i: len(i), (username_length, username, password, ip, port))))
    
    msg = header + msg_type + msg_length + username_length + \
            username + password + ip + port + trailer
            
    return msg


@printargs
def create_invite(ctx, username):
    ci = ClientInvite()
    ci.set_values(
        client_ctx = ctx,
        calle_name_length = len(username),
        calle_name = username,
        num_of_codecs = len(Codecs.values()),
        codec_list = ''.join(Codecs.values()))
        
    return ci.serialize()
    
@printargs
def client_invite_ack(invite):
    cia = ClientInviteAck()
    cia.set_values(
        client_ctx = invite.client_ctx.value,
        call_ctx = invite.call_ctx.value, 
        client_status = ClientStatus.Ringing,
        client_public_ip = invite.client_public_ip.value, 
        client_public_port = invite.client_public_port.value
    )
    return cia.serialize()
    
@printargs
def network_login(username, password):
    login = create_login_msg(username, password)
    client = TcpClient('localhost', 50009)
    client.start()
    time.sleep(0.5)
    client.send(login)
    
@printargs
def login_and_invite(username, password, invited):
    login = create_login_msg(username, password)
    client = TcpClient('localhost', 50009)
    client.start()
    time.sleep(0.5)
    client.send(login)
    print 'going to sleep for about 10 seconds before inviting'
    time.sleep(10)
    print 'username:', username, '>>', string_to_ctx(username)
    ctx = string_to_ctx(username)
    invite = create_invite(ctx, invited)
    print 'invite msg:', repr(invite)
    client.send(invite)
    
def raw_msg():
    queue = Queue.Queue()
    msg = create_login_msg('tzury')
    
    msg = Parser()._body(msg)
    lr = LoginRequest(buf= msg)
    
    print lr.username_length.value, lr.username, lr.password
    
    
def foo():
    print 'foo'
    
    
if __name__ == '__main__':
    if len(sys.argv) > 2:
        fn = sys.argv[1]
        args = sys.argv[2:]
        if fn in locals():
            locals()[fn](*args)
        else:
            print 'usage: (go figure...)'
        