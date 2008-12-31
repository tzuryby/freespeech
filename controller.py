#!/usr/bin/env python
# -*- coding: UTF-8 -*-

__author__ = 'Tzury Bar Yochay'
__version__ = '0.1'
__license__ = 'GPLv3'


import signal, exceptions
from threading import Thread
from twisted.internet import reactor
from serverfactory import serve
from logger import log
import config
import session

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
    log.info( 'termination process started... terminating reactor\'s mainloop')
    reactor.stop()
    #stop flag for threads at session module (started at run_all() function above)
    session.thread_loop_active = False
    
if __name__ == '__main__':
    try:
        signal.signal(signal.SIGINT, stop_all)
        run_all()
        serve(config.Listeners)
    # why there is no signal on windows? 
    except exceptions.KeyboardInterrupt:
        stop_all()