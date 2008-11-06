#! /usr/bin/env python

'''
    **************************************
    ServerFactory (part of freespeech.py)
    **************************************
    
    Exposes unified intefrace for socket server creation
    protocols supproted: tcp, udp.
    
    public objects:
        * serve
        * StreamServer
        * DatagramServer
    
    serve:
        the function serve() returns the thread instance (context) which the server runs in
        the last parameter of the function is a callable object which will be called after each recv
        with the following parameters ((host, port), data)

        examples:
            the following example print out tcp and udp data that arrives at port 50008
            
            # incoming data parser
            def data_handler(addr, data): 
                print 'from: %s:%s - %s' % (addr[0], addr[1], data)
            
            t1 = serve('tcp', 'localhost', 50008, data_handler)
            t2 = serve('udp', 'localhost', 50008, data_handler)
            
    StreamServer:
        the class DatagramServer simply listens to udp packets at a given ip address (addr, port)
        and pass the incoming data plus the address of the sender to a handler is specified
        the constructor is initialized with 3 parameters: address, port and handler
        it expose 2 methods: start() and stop()
        
        example:
            udp_srv = DatagramServer('localhost', 50008, lambda addr, data: data)
            udp_srv.start()     # will open the socket and start the loop
            udp_srv.stop()       # will stop the loop and close the socket
        
    DatagramServer:
        this class dirived from BaseRequestHandler.
        this class can be used by either SocketServer.ThreadingTCPServer or SocketServer.ForkingTCPServer 
        which will attempt to create an instance of it per client.
        Since I wanted to create an hookable generic server I split between the constructor and the __call__.
        In fact, I am passing to ThreadingTCPServer or ForkingTCPServer a new instance of it and not the class itself.
        
        example:
            tcp_srv = SocketServer.ThreadingTCPServer(('localhost', 50008), StreamServer(lambda addr, data: data))
            tcp_srv.serve_forever()
'''

__author__ = 'Tzury Bar Yochay'
__version__ = '0.1'
__license__ = 'GPLv3'
__all__ = ['StreamServer', 'DatagramServer', 'serve']

import sys, threading, uuid

import session

from twisted.internet.protocol import Protocol, Factory, ServerFactory
from twisted.internet import reactor

from threading import Thread
from utils import Storage

class TcpServer(Protocol):
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
        
class TcpServerFactory(ServerFactory):
    def __init__(self, id):
        self.protocol = TcpServer
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
                print 'TcpServerFactory.send_to', (host, port), repr(data)
                e.transport.write(data)
                return True
                
    def connected_to(self, (host, port)):
        for e in self.echoers:
            if e.transport.client == (host, port):
                return True

def start_tcp(port):
    id = uuid.uuid4().hex
    # todo: pass this id to the handler so we don't have to look for it at serverpool.send_to
    tcp_server = TcpServerFactory(id)
    session.servers_pool.add(id, 'tcp', tcp_server)
    reactor.listenTCP(port, tcp_server())
    reactor.run(installSignalHandlers=0)

def start_udp(port):
    pass
    '''id = uuid.uuid4().hex
    # todo: pass this id to the handler so we don't have to look for it at serverpool.send_to
    tcp_server = TcpServerFactory(id)
    session.servers_pool.add(id, 'tcp', tcp_server)
    reactor.listenTCP(port, tcp_server())
    reactor.run(installSignalHandlers=0)
    '''
def serve(proto, port):
    
    targets = {'tcp': start_tcp,'udp': start_udp}
    
    if proto in targets:
        t = Thread(target = targets[proto], args = (port,))
        t.start()
        print 'serving %s at localhost:%s' % (proto, port)
