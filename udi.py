#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from __future__ import with_statement

__author__ = 'Tzury Bar Yochay'
__version__ = '0.1'
__license__ = 'GPLv3'


from snoipclient import SnoipClient
import time

sc = SnoipClient(('0.0.0.0', 50009))
time.sleep(1)
sc.login('120', 'a120----------------')

time.sleep(3)

sc.send_keep_alive()

time.sleep(24)
