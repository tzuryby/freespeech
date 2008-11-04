import sys, time

threads = []
TOTALSWITCHES = 10**6
NUMTHREADS    = 10**5

def null_factory():
    def empty():
        while 1: 
            yield None
    return empty()

def quitter():
    for n in xrange(TOTALSWITCHES/NUMTHREADS):
        yield None

def scheduler():
    global threads
    try:
        while 1:
            for thread in threads: 
                thread.next()
    except StopIteration:
        print 'stopping'

if __name__ == "__main__":
    for i in xrange(NUMTHREADS):
        threads.append(null_factory())
    threads.append(quitter())
    starttime = time.clock()
    scheduler()
    print "TOTAL TIME:    ", time.clock()-starttime
    print "TOTAL SWITCHES:", TOTALSWITCHES
    print "TOTAL THREADS: ", NUMTHREADS