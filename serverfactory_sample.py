import serverfactory
#~ import time 
#~ from threading import Thread

clients = {}

def register(client, request, proto, id):
    clients[client] = (request, proto, id)
    print clients
    
def handler(client, msg, id):
    print 'from', client, msg
    if clients[client][1] == 'tcp':
        clients[client][0].send('reply: ' + msg)
    elif clients[client][1] == 'udp':
        clients[client][0].send(msg, client)
    
    
def main():
    serverfactory.serve('tcp', 'localhost', 50009, handler, register)
    serverfactory.serve('udp', 'localhost', 50009, handler, register)

        
if __name__ == '__main__':
    main()
    #Thread(target = send_test).start()