#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import with_statement
import sys
import socket
import struct
import time
import Queue

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
            data = self.socket.recv(1024*6)
            print 'recieved:', repr(data)
            self.recv_callback and self.recv_callback(data)
            
    def close(self):
        self.socket.close()
            
class SnoipClient(object):
    
    def __init__(self, (host, port)):
        self.call_ctx  = None
        self.client_ctx = None
        self.username = None
        self.client = TcpClient((host, port), self.recv)
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
                self.ack_invite(msg)
            elif isinstance(msg, ServerForwardRing):
                self.invited_ctx = msg.client_ctx.value
                print '60:current call_ctx', repr(self.call_ctx), 'new call_ctx', repr(msg.call_ctx.value)
                self.call_ctx = msg.call_ctx.value
                print 'ringing...'
            elif isinstance(msg, ClientAnswer):
                self.invited_ctx = msg.client_ctx.value
                print 'call was answered by other party...'
            elif isinstance(msg, ClientRTP):
                self.rtp_received(msg)
                
                
    def login(self, username, password):
        self.username = username
        print 'snoipclient-login'
        data = create_login_msg(username, password)
        self._send(data)
        
    def login_reply(self, msg):
        print 'snoipclient-login_reply'
        self.client_ctx = msg.client_ctx.value
        self.client_public_ip = msg.client_public_ip.value
        self.client_public_port = msg.client_public_port.value
        
    def invite(self, username):
        print 'snoipclient-invite'
        data = create_invite(self.client_ctx, username)
        self._send(data)
        
    def ack_invite(self, sfi):
        print 'snoipclient-ack_invite'
        print '87:current call_ctx', repr(self.call_ctx), 'new call_ctx', repr(sfi.call_ctx.value)
        self.call_ctx = sfi.call_ctx.value
        data = client_invite_ack(sfi)
        self._send(data)
        time.sleep(3)
        self.answer()
        
    def answer(self):
        print 'snoipclient-answer'
        ca = ClientAnswer()
        ca.set_values(client_ctx=self.client_ctx, call_ctx=self.call_ctx, codec=Codecs.values()[0])
        print 'answering a ring of call_ctx:', repr(self.call_ctx)
        self._send(ca.pack())
        
    def _send(self, data):
        self.client.send(data)
        
    def feed_rtp(self, rtp_bytes, seq):
        crtp = ClientRTP()
        crtp.set_values(client_ctx=self.invited_ctx, call_ctx=self.call_ctx, 
            sequence=seq, rtp_bytes_length=len(rtp_bytes), rtp_bytes=rtp_bytes)
        self._send(crtp.pack())
        
    def rtp_received(self, msg):
        bytes = msg.rtp_bytes.value
        with open(self.username + '_incoming_rtp', 'a') as f:
            f.write(bytes + '\n')
                
    def send_keep_alive(self):
        ka = KeepAlive()
        ka.set_values( client_ctx = self.client_ctx, 
            client_public_ip=self.client_public_ip,
            client_public_port=self.client_public_port)
            
        self._send(ka.pack())
        
def create_login_msg(username, password='0'*20):
    header = '\xab\xcd'
    trailer = '\xdc\xba'
    msg_type = '\x00\x02'
    
    username_length = struct.pack('!b', len(username))
    username = struct.pack('!%dc' % len(username), *(username))
    password = struct.pack('!20c',*(password))
    ip = struct.pack('!16b', *(0 for i in xrange(16)))
    port = struct.pack('!i', 0)
    msg_length = struct.pack('!h',  sum(map(lambda i: len(i), (username_length, username, password, ip, port))))
    
    msg = header + msg_type + msg_length + username_length + \
            username + password + ip + port + trailer
            
    return msg


def create_invite(ctx, username):
    ci = ClientInvite()
    ci.set_values(
        client_ctx = ctx,
        calle_name_length = len(username),
        calle_name = username,
        num_of_codecs = len(Codecs.values()),
        codec_list = ''.join(Codecs.values()))
        
    return ci.pack()
    
def client_invite_ack(invite):
    cia = ClientInviteAck()
    cia.set_values(
        client_ctx = invite.client_ctx.value,
        call_ctx = invite.call_ctx.value, 
        client_status = ClientStatus.Ringing,
        client_public_ip = invite.client_public_ip.value, 
        client_public_port = invite.client_public_port.value
    )
    
    print 'will ack invite of call_ctx:', repr(invite.call_ctx.value)
    return cia.pack()
