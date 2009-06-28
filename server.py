#!/usr/bin/env python
# -*- coding: UTF-8 -*-


__author__ = 'Tzury Bar Yochay'
__version__ = '0.1'
__license__ = 'GPLv3'


import sys
from twisted.internet import reactor
from serverfactory import serve
from logger import log
import config
import session
from daemon import Daemon

import signal, exceptions
from threading import Thread

from struct import unpack
from cPickle import loads

from logging import makeLogRecord
from logging.handlers import DEFAULT_TCP_LOGGING_PORT
from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor


# ***********************************************************
# SNOIP DAEMON
# ***********************************************************

class SnoipDaemon(Daemon):
    def run_all(self):
        functions = (
            session.handle_inbound_queue, 
            session.handle_outbound_queue, 
            session.remove_old_clients, 
        )
        
        for fn in functions:
            Thread(target=fn).start()
            
    def stop_all(self, *args):
        #stop the reactor
        if not reactor._stopped:
            log.info("termination process started... "
                "terminating reactor's mainloop")
            reactor.stop()
        
        #stop flag for threads at session module started at run_all() function
        session.thread_loop_active = False
    
    def run(self):
        self.run_all()
        serve(config.Listeners)
        
    def stop(self):
        self.stop_all()
        Daemon.stop(self)
        
'''        
# ***********************************************************
# LOG DAEMON
# ***********************************************************

allow_clients = ['localhost', '127.0.0.1', ]
lan = '10.0.0.'

class LoggingProtocol(Protocol):
    def __init__(self):
        self.data = "" # definitely must be bytes, not unicode
        self.slen = None

    def connectionMade(self):
        client_host = self.transport.client[0]
        
        if client_host in allow_clients or client_host.startswith(lan):
            print 'adding client', client_host
            self.factory.echoers.append(self)
        else:
            print 'refuses adding client', client_host
            
    def dataReceived(self, data):
        """Handle data from the log sender."""
        self.data += data

        # grab the length field from the first 4 bytes of the message
        if not self.slen and len(self.data) >= 4:
            self.slen = unpack(">L", self.data[:4])[0]

        # handle a chunk (be careful in case we have data from the next chunk)
        if self.slen and len(self.data) >= self.slen + 4:
            self.handle_chunk(self.data[4:self.slen + 4])
            self.data = self.data[self.slen + 4:]
            self.slen = None

    def handle_chunk(self, chunk):
        record = makeLogRecord(loads(chunk))
        self.factory.send_others(self.transport.client, record.msg + '\r\n')
        
class LoggingFactory(Factory):
    protocol = LoggingProtocol
    echoers = []

    def _broadcast(self, targets, data):
        for target in targets:
            target.transport.write(data)
            
    def send_others(self, (host, port), data):
        self._broadcast((echo for echo in self.echoers 
            if echo.transport.client != (host, port)), data)
        
    def send_all(self, data):
        self._broadcast(self.echoers, dir(data))

class LogDaemon(Daemon):
    def startLogging(self):
        listener = reactor.listenTCP(
            DEFAULT_TCP_LOGGING_PORT, LoggingFactory())
            
        allow_clients.append(listener.getHost().host)
        print allow_clients
        reactor.run(installSignalHandlers=0)
        
    def stopLogging(self):
        if not reactor._stopped:
            reactor.stop()
            
    def run(self):
        self.startLogging()
        
    def stop(self):
        self.stopLogging()
        Daemon.stop(self)
'''

snoip_daemon = SnoipDaemon('/tmp/snoip_daemon.pid')
#log_daemon = LogDaemon('/tmp/snoip_log_daemon.pid')

def start_console_mode():
    try:
        signal.signal(signal.SIGINT, snoip_daemon.stop_all)
        snoip_daemon.run_all()
        serve(config.Listeners)
    # why there is no signal on windows? 
    except exceptions.KeyboardInterrupt:
        snoip_daemon.stop_all()    

daemonizer = {
    'snoip': 
    { 
        'start': snoip_daemon.start, 
        'stop': snoip_daemon.stop, 
        'restart': snoip_daemon.restart
    }
'''    ,
    'log': 
    { 
        'start': log_daemon.start, 
        'stop': log_daemon.stop, 
        'restart': log_daemon.restart
    }
'''    
}

help_message = '''    
USAGE:
Start as console application
$ python server.py 

Treat as Daemon:
$ python server.py start|stop|restart
'''

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 1:
        start_console_mode()
    elif sys.argv[1] in ('help', '--help', 'h', '-h'):
        print help_message
    elif len(sys.argv) == 2:
        daemon = 'snoip' #sys.argv[1]
        action = sys.argv[1]
        #if daemon in daemonizer:
        if action in daemonizer[daemon]:
            daemonizer[daemon][action]()