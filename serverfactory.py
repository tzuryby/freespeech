#!/usr/bin/env python
# -*- coding: UTF-8 -*-


__author__ = 'Tzury Bar Yochay'
__version__ = '0.1'
__license__ = 'GPLv3'


import sys, threading, time
import logging, cPickle, exceptions
from threading import Thread

from twisted.internet.protocol import (
    Protocol, DatagramProtocol, Factory, ServerFactory
    )
from twisted.internet import reactor

import session
from utils import Storage
from logger import log

from logging import makeLogRecord, getLogger
from logging.config import fileConfig
from logging.handlers import DEFAULT_TCP_LOGGING_PORT

class TCPServerPrtocol(Protocol):
    dataReceivedHandler = session.recv_msg
        
    def connectionMade(self):
        self.factory.echoers.append(self)
        log.info('tcp_connection from %s' % repr(self.transport.client))
        
    def dataReceived(self, data):
        if not (host, port) in self.factory.echoers:
            self.factory.echoers.append((host, port))
            
        host, port = self.transport.client
        self.dataReceivedHandler((host, port), data)
        
    def connectionLost(self, reason):
        #todo: -> remove this client form the session_ctx_table
        log.info('connection Lost')
        self.factory.echoers.remove(self)
        
        
class TCPServerFactory(ServerFactory):
    protocol = TCPServerPrtocol
    echoers = []
        
    def _broadcast(self, clients, data):
        for client in clients:
            client.transport.write(data)
            
    def send_others(self, (host, port), data):
        self._broadcast([echo for echo in self.echoers 
            if echo.transport.client != (host, port)], data)
        
    def send_all(self, data):
        self._broadcast(self.echoers, data)
            
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
        

def serve(listeners):
    starters = {
        'tcp': TCPServerFactory,
        'udp': UDPServer }
    
    reactor_listen = {
        'tcp': reactor.listenTCP,
        'udp': reactor.listenUDP }
    
    for proto, port in listeners:
        starter = starters[proto]()
        reactor_listen[proto](port, starter)
        session.servers_pool.add(proto, starter)
        log.info( 'serving %s on port %s' % (proto, port))
        
    #~ reactor.listenTCP(logging.DEFAULT_TCP_LOGGING_PORT, BroadcastFactory())
    reactor.run(installSignalHandlers=0)
    