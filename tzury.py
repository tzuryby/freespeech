from __future__ import with_statement
from snoipclient import SnoipClient
import time

# init a client at snoip port
sc = SnoipClient(('', 50009))

#login 
sc.login('tzury', '0'*20)

#pause and let replies arrive
time.sleep(3)

#send invite
sc.invite('udi')

#pause and let replies arrive
time.sleep(10)

with open('data.rtp', 'r') as lines:
    for line in lines:
        sc.feed_rtp(line)
        time.sleep(1)
