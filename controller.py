
from threading import Thread
from serverfactory import serve
import config
import session


def run_all():
    threads = [session.handle_inbound_queue, 
        session.handle_outbound_queue, 
        session.remove_old_clients]
        
    for thread in threads:
        Thread(target = thread).start()
        
if __name__ == '__main__':
    run_all()
    serve(config.Listeners)