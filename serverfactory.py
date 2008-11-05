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

#~ from socket import *
#~ from SocketServer import *


#~ #TCP
#~ class StreamServer(BaseRequestHandler):
    #~ def __init__(self, handler=None, register=None):
        #~ self.run = True
        #~ self.handler = handler
        #~ self.register = register
        #~ self.id = uuid.uuid4()
        
    #~ # nice hack! super.__init__ will be called
    #~ def __call__(*args):
        #~ BaseRequestHandler.__init__(*args)
    
    #~ def setup(self):
        #~ print self.client_address, 'connected!'
        #~ if self.register:
            #~ self.register(self.client_address, self, 'tcp', self.id)
        
    #~ def handle(self):
        #~ data = 'dummy'
        #~ while data and self.run:
            #~ data = self.request.recv(4*1024)
            #~ if data and self.handler:
                #~ print 'server received:', self.client_address, data
                #~ self.handler(self.client_address, data)
    
    #~ def send(self, msg):
        #~ self.request.send(msg)
              
    #~ def finish(self):
        #~ print self.client_address, 'disconnected!'
        #~ self.request.send('bye ' + str(self.client_address) + '\n')
        
#~ #UDP        
#~ class DatagramServer(object):
    #~ def __init__(self, addr, port, handler=None, register=None):
        #~ self.addr = addr
        #~ self.port = port
        #~ self.handler = handler
        #~ self.register = register
        #~ self.socket = socket(AF_INET,SOCK_DGRAM)
        #~ self.id = uuid.uuid4()
        #~ self.run = True
                
    #~ def start(self):
        #~ try:
            #~ self.socket.bind((self.addr, self.port))
            #~ while self.run:
                #~ data, addr = self.socket.recvfrom(4*1024)
                #~ if data:
                    #~ print 'server received:', self.client_address, data
                    #~ if self.register:
                        #~ self.register(addr, self, 'udp', self.id)
                    #~ if self.handler:
                        #~ self.handler(addr, data)
                
            #~ self.socket.close()
        #~ except Exception, e:
            #~ pass
        
    #~ def send(self, msg, addr):
        #~ self.socket.sendto(msg, addr)
        
    #~ def stop(self):
        #~ try:
            #~ self.run = False
            #~ self.socket.close()
        #~ except:
            #~ pass

#~ def serve(proto, addr, port, handler, register):
    #~ def tcp(addr, port, handler, register):
        #~ req_handler = StreamServer(handler, register)
        #~ SocketServer.ThreadingTCPServer((addr, port), req_handler).serve_forever()
    
    #~ def udp(addr, port, handler, register):
        #~ DatagramServer(addr, port, handler, register).start()
    
    #~ targets = {'tcp': tcp, 'udp': udp}
    
    #~ if proto in targets:
        #~ t = Thread(target = targets[proto], args = (addr, port, handler, register))
        #~ t.start()
        #~ print 'serving %s at %s:%s' % (proto, addr, port)
        
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
    
def serve(proto, port):
    
    def udp(port):
        pass #DatagramServer(port, handler).start()
    
    targets = {'tcp': start_tcp} #, 'udp': udp}
    
    if proto in targets:
        t = Thread(target = targets[proto], args = (port,))
        t.start()
        print 'serving %s at localhost:%s' % (proto, port)
