import sys
import socket
import struct
import time

import Queue
from messageparser import Packer, Parser
from threading import Thread
from messages import *
from config import Codecs
from decorators import printargs


from twisted.internet import reactor
from twisted.internet.protocol import Protocol, ClientCreator
from sys import stdout


class TcpClient(Thread):
    def __init__(self, host, port):
        Thread.__init__(self)
        self.host, self.port= host, port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print 'connecting..'
        self.socket.connect((self.host, self.port))
        print 'connected!'

    def send(self, msg):
        print 'TcpClient.send:', msg
        self.socket.send(msg)
                        
    def run(self):
        data = 'dummy'
        while data:
            data = self.socket.recv(1024*4)
            print 'recieved:', repr(data)
            
    def close(self):
        self.socket.close()
            
def create_login_msg(username, password='0'*20):
    lr = LoginRequest()
    lr.set_values(
    
    )
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
        