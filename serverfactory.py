#! /usr/bin/env python

__author__ = 'Tzury Bar Yochay'
__version__ = '0.1'
__license__ = 'GPLv3'


import sys, threading, uuid, time
from threading import Thread

from twisted.internet.protocol import Protocol, DatagramProtocol, ServerFactory
from twisted.internet import reactor

import session
from utils import Storage
        
class TCPServer(Protocol):
    dataReceivedHandler = session.recv_msg
        
    def connectionMade(self):
        self.factory.echoers.append(self)
        print 'tcp_connection from', self.transport.client
        
    def dataReceived(self, data):
        host, port = self.transport.client
        self.dataReceivedHandler((host, port), data)
        
    def connectionLost(self, reason):
        #todo: -> remove this client form the session_ctx_table
        
        print 'connection Lost'
        self.factory.echoers.remove(self)
        

class TCPServerFactory(ServerFactory):
    def __init__(self, id):
        self.protocol = TCPServer
        self.echoers = []
        self.id = id
        
    # I instansiate before passing to reactor.listenTCP thus must have __call__
    def __call__(self):    
        return self
        
    def send_all(self, data):
        for e in self.echoers:
            e.transport.write(data)
            
    def send_to(self, (host, port), data):
        for e in self.echoers:
            if e.transport.client == (host, port):
                print 'TCPServerFactory.send_to', (host, port), repr(data)
                e.transport.write(data)
                return True
                
    def connected_to(self, (host, port)):
        for e in self.echoers:
            if e.transport.client == (host, port):
                return True

class UDPServer(DatagramProtocol):
    echoers = []
    dataReceivedHandler = session.recv_msg
    
    def __init__(self):
        pass
        
    def __call__(self):
        return self
        
    def startProtocol(self):
        pass
        
    def datagramReceived(self, data, (host, port)):
        print 'received:', (host, port), data
        if not (host, port) in self.echoers:
            self.echoers.append((host, port))
        
        self.dataReceivedHandler((host, port), data)
    
    def send_to(self, (host, port), data):
        if self.connected_to((host, port)):
            self.transport.write(data, (host, port))

    def connected_to(self, (host, port)):
        return (host, port) in self.echoers



def start_tcp():
    id = uuid.uuid4().hex
    tcp_server = TCPServerFactory(id)
    session.servers_pool.add(id, 'tcp', tcp_server)
    return tcp_server

def start_udp():
    id = uuid.uuid4().hex
    udp_server = UDPServer()
    session.servers_pool.add(id, 'udp', udp_server)
    return udp_server

def serve(listeners):
    starters = {
        'tcp': start_tcp,
        'udp': start_udp }
    
    reactor_invoke = {
        'tcp': reactor.listenTCP,
        'udp': reactor.listenUDP }
    
    for proto, port in listeners:
        reactor_invoke[proto](port, starters[proto]())
        print 'serving %s on port %s' % (proto, port)
        
    reactor.run(installSignalHandlers=0)
    
