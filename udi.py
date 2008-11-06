from snoipclient import SnoipClient

SnoipClient(('localhost', 50009)).login('udi', '0'*20)
