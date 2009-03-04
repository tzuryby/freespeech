from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from logger import log


# Here's a UDP version of the simplest possible protocol
class UDPServer(DatagramProtocol):
    def datagramReceived(self, datagram, address):
        print 'received: %d bytes' % len(datagram)


class UDPClient(DatagramProtocol):
    
    def startProtocol(self):
        self.transport.connect('127.0.0.1', 8000)
        self.sendDatagram()
    
    def sendDatagram(self):
        lines = (line for line in open('large_data.rtp', 'r'))
        for line in lines:
            self.transport.write(line)
            
    def datagramReceived(self, datagram, host):
        print 'Datagram received %d bytes' % len(datagram)
        self.sendDatagram()


def main():
    reactor.listenUDP(8000, UDPServer())
    protocol = UDPClient()
    t = reactor.listenUDP(0, protocol)    
    reactor.run()




if __name__ == '__main__':
    main()
