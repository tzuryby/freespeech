#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import with_statement
from snoipclient import SnoipClient
import time
from logger import log

sc = SnoipClient(('localhost', 50009))
sc.login('123', 'a123' + '-'*16)

while True:
    time.sleep(10)
    sc.send_keep_alive()
    