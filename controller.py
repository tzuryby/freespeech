
from threading import Thread
from serverfactory import serve
import config
import session


def run_all():
    threads = [session.handle_requests, session.handle_replies, session.remove_old_clients]
    for thread in threads:
        Thread(target = thread).start()
        
if __name__ == '__main__':
    for proto, host, port in config.Listeners:
        serve(proto, port)
    run_all()