#!/usr/bin/env python

import threading, signal, exceptions
from threading import Thread
from twisted.internet import reactor
from serverfactory import serve

import config
import session



def run_all():
    threads = [session.handle_inbound_queue, 
        session.handle_outbound_queue, 
        session.remove_old_clients]
        
    for thread in threads:
        Thread(target = thread).start()
        
        
def stop_all(*args):
    
    #stop the reactor
    print '\ntermination process started...\nterminating reactor\'s mainloop'
    reactor.stop()
    #stop flag for threads at session module (started at start_all() function above)
    session.thread_loop_active = False
    

signal.signal(signal.SIGINT, stop_all)    

if __name__ == '__main__':
    try:
        run_all()
        serve(config.Listeners)
    # why there is no signal on windows? 
    except exceptions.KeyboardInterrupt:
        stop_all()