#!/usr/bin/env python
# -*- coding: UTF-8 -*-

__author__ = 'Tzury Bar Yochay'
__version__ = '0.1'
__license__ = 'GPLv3'


import sys, threading, time
import logging, cPickle, exceptions
from threading import Thread

from twisted.internet.protocol import Protocol, DatagramProtocol, ServerFactory
from twisted.internet import reactor

import session
from utils import Storage
from logger import log

        
class TCPServer(Protocol):
    dataReceivedHandler = session.recv_msg
        
    def connectionMade(self):
        self.factory.echoers.append(self)
        log.info('tcp_connection from %s' % repr(self.transport.client))
        
    def dataReceived(self, data):
        host, port = self.transport.client
        self.dataReceivedHandler((host, port), data)
        
    def connectionLost(self, reason):
        #todo: -> remove this client form the session_ctx_table
        log.info('connection Lost')
        self.factory.echoers.remove(self)
        
    
class TCPServerFactory(ServerFactory):
    protocol = TCPServer
    echoers = []
        
    def send_all(self, data):
        for e in self.echoers:
            e.transport.write(data)
            
    def send_to(self, (host, port), data):
        for e in self.echoers:
            if e.transport.client == (host, port):
                #print 'TCPServerFactory.send_to', (host, port), repr(data)
                e.transport.write(data)
                return True
                
    def connected_to(self, (host, port)):
        for e in self.echoers:
            if e.transport.client == (host, port):
                return True

class UDPServer(DatagramProtocol):
    echoers = []
    dataReceivedHandler = session.recv_msg
    
    def startProtocol(self):
        pass
        
    def datagramReceived(self, data, (host, port)):
        if not (host, port) in self.echoers:
            self.echoers.append((host, port))
        
        self.dataReceivedHandler((host, port), data)
    
    def send_all(self, data):
        for (host, port) in self.echoers:
            self.send_to((host, port), data)
            
    def send_to(self, (host, port), data):
        if self.connected_to((host, port)):
            self.transport.write(data, (host, port))

    def connected_to(self, (host, port)):
        return (host, port) in self.echoers
        

class BroadcastServer(TCPServer):
    def dataReceived(self, data):
        self.factory.send_all(data)

class BroadcastLoggingServer(BroadcastServer):
    def dataReceived(self, data):
        try:
            data = cPickle.loads(data)
        except exceptions.EOFError:
            pass
        data = logging.makeLogRecord(data)
        BroadcastServer.dataReceived(data)


start_tcp = TCPServerFactory
start_udp = UDPServer

def serve(listeners):
    starters = {
        'tcp': start_tcp,
        'udp': start_udp }
    
    reactor_listen = {
        'tcp': reactor.listenTCP,
        'udp': reactor.listenUDP }
    
    for proto, port in listeners:
        starter = starters[proto]()
        reactor_listen[proto](port, starter)
        session.servers_pool.add(proto, starter)
        log.info( 'serving %s on port %s' % (proto, port))
        
    #broadcast = TCPServerFactory()
    #broadcast.protocol = BroadcastLoggingServer
    #reactor.listenTCP(9020,broadcast)
        
    reactor.run(installSignalHandlers=0)
    