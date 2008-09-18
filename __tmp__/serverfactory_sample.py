import serverfactory

def data_handler(addr, data):
    print '%s:%s\t%s' % (addr[0], addr[1], data)
    
def main():
    serverfactory.serve('tcp', 'localhost', 50009, data_handler)
    serverfactory.serve('udp', 'localhost', 50009, data_handler)


if __name__ == '__main__':
    main()