import serverfactory


clients = {}

def register(client, request, proto):
    clients[client] = (request, proto)
    print clients
    
def handler(client, msg):
    print 'from', client, msg
    if clients[client][1] == 'tcp':
        clients[client][0].send('reply: ' + msg)
    elif clients[client][1] == 'udp':
        print 'attempt to send udp'
        clients[client][0].send(msg, client)
    
    
def main():
    serverfactory.serve('tcp', 'localhost', 50009, handler, register)
    serverfactory.serve('udp', 'localhost', 50009, handler, register)


if __name__ == '__main__':
    main()