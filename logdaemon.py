#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""A Twisted receiver for messages sent by Python logging's SocketHandler.

The format used by SocketHandler is a 4-byte length record followed by a pickle
containing the log data.

"""
import sys

from struct import unpack
from cPickle import loads

from logging import makeLogRecord
from logging.handlers import DEFAULT_TCP_LOGGING_PORT
from twisted.internet.protocol import Protocol, Factory

from daemon import Daemon
from twisted.internet import reactor

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

def startLogging():
    listener = reactor.listenTCP(DEFAULT_TCP_LOGGING_PORT, LoggingFactory())
    allow_clients.append(listener.getHost().host)
    print allow_clients
    reactor.run(installSignalHandlers=0)
    
def stopLogging():
    if not reactor._stopped:
        reactor.stop()

class SnoipDaemon(Daemon):
    def run(self):
        startLogging()
        
    def stop(self):
        stopLogging()
        Daemon.stop(self)

snoip_log_daemon = SnoipDaemon('/tmp/snoip_log_daemon.pid')

if __name__ == '__main__':
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            snoip_log_daemon.start()
        elif 'stop' == sys.argv[1]:
            snoip_log_daemon.stop()
        elif 'restart' == sys.argv[1]:
            snoip_log_daemon.restart()
        elif 'fg' == sys.argv[1]:
            startLogging()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)