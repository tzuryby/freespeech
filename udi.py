from __future__ import with_statement
from snoipclient import SnoipClient
import time

sc = SnoipClient(('localhost', 50009))
sc.login('udi', '0'*20)

time.sleep(18)
print 'I will feed you this organic RTP'
with open('data.rtp', 'r') as lines:
    for line in lines:
        sc.feed_rtp(line)
        time.sleep(3)
