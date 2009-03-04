#!/usr/bin/env python
# -*- coding: UTF-8 -*-


__author__ = 'Tzury Bar Yochay'
__version__ = '0.1'
__license__ = 'GPLv3'


import sys
from threading import Thread
from twisted.internet import reactor
from serverfactory import serve
from logger import log
import config
import session
from daemon import Daemon

def run_all():
    functions = (
        session.handle_inbound_queue, 
        session.handle_outbound_queue, 
        session.remove_old_clients, 
    )
    
    for fn in functions:
        Thread(target=fn).start()
        
def stop_all(*args):
    #stop the reactor
    if not reactor._stopped:
        log.info("termination process started... terminating reactor's mainloop")
        reactor.stop()
    
    #stop flag for threads at session module (started at run_all() function above)
    session.thread_loop_active = False

class SnoipDaemon(Daemon):
    def run(self):
        run_all()
        serve(config.Listeners)
        
    def stop(self):
        stop_all()
        Daemon.stop(self)

snoip_daemon = SnoipDaemon('/tmp/snoip_daemon.pid')

if __name__ == '__main__':
	if len(sys.argv) == 2:
		if 'start' == sys.argv[1]:
			snoip_daemon.start()
		elif 'stop' == sys.argv[1]:
			snoip_daemon.stop()
		elif 'restart' == sys.argv[1]:
			snoip_daemon.restart()
		else:
			print "Unknown command"
			sys.exit(2)
		sys.exit(0)
	else:
		print "usage: %s start|stop|restart" % sys.argv[0]
		sys.exit(2)
