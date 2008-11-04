# duplex server test

from server
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
    

duplex_server('tcp', '', 50010, handler, register)
duplex_server('udp', '', 50010, handler, register)