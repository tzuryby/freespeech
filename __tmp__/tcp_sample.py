class TCPEchoRequestHandler(SocketServer.BaseRequestHandler):
    def __init__(self, handler = None):
        self.handler = handler
        
    def setup(self):
        print self.client_address, 'connected!'
        self.request.send('hi ' + str(self.client_address) + '\n')

    def handle(self):
        data = 'dummy'
        while data:
            self.request.send(data)
            data = self.request.recv(1024)
            if data.strip() == 'bye':
                break
            if self.handler:
                self.handler(data)
            

    def finish(self):
        print self.client_address, 'disconnected!'
        self.request.send('bye ' + str(self.client_address) + '\n')