# udp_stress_server.py by Eli Fulkerson
# http://www.elifulkerson.com for updates and documentation
# You will also need udp_stress_client.py for this to do anything for you.

# "Push it to the limit!"

# This is an extremely quick-and-dirty UDP testing utility.
# All it does is shove a bunch of UDP traffic through to the server, which
# records and reports the amount of data successfully recieved and the time
# that the transmission took.  It spits out the ratio to give a rough kbps
# estimate.

# The results are very dependent on how much data you push through.  Low amounts
# of data will give you artificially low results.

# "Safety is not guaranteed."

# June 24 2006

from socket import *
# Create socket and bind to address
UDPSock = socket(AF_INET,SOCK_DGRAM)
UDPSock.bind(('',50008))

while 1:
    data,addr = UDPSock.recvfrom(4*1024)
    
    if not data:
        print "No data."
        break
    else:
        print 'from:', addr, ' data:', data
UDPSock.close()
