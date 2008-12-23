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

#send invite
sc.invite('120')

#pause and let replies arrive
time.sleep(8)

with open('large_data.rtp', 'r') as lines:
    i = 0
    for line in lines:
        sc.feed_rtp(line, i)
        i+=1
        time.sleep(1)
        
