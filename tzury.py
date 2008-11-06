from snoipclient import SnoipClient
import time

sc = SnoipClient(('', 50009))
sc.login('tzury', '0'*20)

time.sleep(5)

sc.invite('udi')