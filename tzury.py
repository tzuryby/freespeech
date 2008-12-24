#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import with_statement
from snoipclient import SnoipClient
import time

# init a client at snoip port
sc = SnoipClient(('localhost', 50009))

#login 
sc.login('121', 'a121----------------')

#pause and let replies arrive
time.sleep(3)

sc.send_keep_alive()
time.sleep(1)

#send invite
sc.invite('120')

#pause and let replies arrive
time.sleep(4)

with open('large_data.rtp', 'r') as lines:
    i = 0
    for line in lines:
        sc.feed_rtp(line, i)
        i+=1
        time.sleep(0.5)
        
sc.request_hangup()
