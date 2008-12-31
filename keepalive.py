#!/usr/bin/env python
# -*- coding: UTF-8 -*-

__author__ = 'Tzury Bar Yochay'
__version__ = '0.1'
__license__ = 'GPLv3'


from __future__ import with_statement
from snoipclient import SnoipClient
import time
from logger import log

sc = SnoipClient(('localhost', 50009))
sc.login('123', 'a123' + '-'*16)

while True:
    time.sleep(10)
    sc.send_keep_alive()
    