"""A Twisted receiver for messages sent by Python logging's SocketHandler.

The format used by SocketHandler is a 4-byte length record followed by a pickle
containing the log data.

To start the receiver, use bin/logreceiver.tac::

    twistd --python=bin/logreceiver.tac

"""
from struct import unpack
from cPickle import loads

from logging import makeLogRecord, getLogger
from logging.config import fileConfig
from logging.handlers import DEFAULT_TCP_LOGGING_PORT

from twisted.application.service import Application
from twisted.application.internet import TCPServer
from twisted.internet.protocol import Protocol, Factory


class Logging(Protocol):
    def __init__(self):
        self.data = "" # definitely must be bytes, not unicode
        self.slen = None

    def connectionMade(self):
        self.factory.echoers.append(self)
        log.info('tcp_connection from %s' % repr(self.transport.client))
    
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
        logger = getLogger(record.name)
        logger.handle(record)
        
        
class LoggingFactory(Factory):
    protocol = Logging
    echoers = []

    def _broadcast(self, clients, data):
        for client in clients:
            client.transport.write(data)
            
    def send_others(self, (host, port), data):
        self._broadcast([echo for echo in self.echoers 
            if echo.transport.client != (host, port)], data)
        
    def send_all(self, data):
        self._broadcast(self.echoers, data)

service = TCPServer(DEFAULT_TCP_LOGGING_PORT, LoggingFactory())
application = Application("Log Receiver")
service.setServiceParent(application)