from __future__ import with_statement
from snoipclient import SnoipClient
import time

sc = SnoipClient(('localhost', 50009))
sc.login('udi', '0'*20)