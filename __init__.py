#!/usr/bin/env python

import utils
import db
import serverfactory
import messages
import messageparser
import REThread
import threadpool
import codecs
import daemon

from utils import *
from db import *
from serverfactory import *
from messages import *
from messageparser import *
from REThread import *
from threadpool import *
from codecs import *
from daemon import *



def test_packer():
    '''
        >>> queue = Queue.Queue()
        >>> packer = Packer(queue)
        >>> packer.pack(('client-01', '\xab\xcd\x01\x00'))
        >>> packer.pack(('client-01', '\x09\xcc\xdd'))
        >>> packer.pack(('client-01', '\xdc\xba'))
        >>> queue.get()
        ('client-01', ('\x01', <ctypes.c_char_Array_9 object at 0xb7dd6974>))
        >>> packer.pack(('client-02', '\xab\xcd\x00\x00\x09\x01\xdd\xdc\xba'))
        >>> queue.get()
        ('client-02', ('\x01', <ctypes.c_char_Array_9 object at 0xb7dd6974>))
    '''
    pass
    
def test_parser():
    '''
        >>> p = Parser()
        >>> invalid_msg = '\xab\xcd\x01\x00\x09\x01\x01\x01\xdc\xba'
        >>> valid_msg = '\xab\xcd\x01\x00\x09\x01\x01\xdc\xba'
        >>> not p.valid(invalid_msg)
        True
        >>> p.valid(valid_msg)
        True
        >>> Parser().body(valid_msg)
        ('\x01', '\x01\x01')
        >>> Parser().body(invalid_msg)
        False
    '''
    
if __name__ == "__main__":
    # won't work since doctest have a problem parsing the bytes compound the message
    # however these lines were pasted from the toplevel py interperter and worl there fine
    #import doctest
    #doctest.testmod()
    buf = ['\x08'                                                                               # username_length
           '\x71\x72\x73\x74\x75\x76\x77\x78'                                                   # usrname
           '\x72\x73\x74\x75\x76\x77\x78\x79\x69\x68\x67\x66\x70\x71\x72\x73\x74\x75\x76\x77'   # password
            '\x78\x79\x69\x68\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'                  # local_ip
           '\x00\x00\x13\x90']                                                                  # port
    
    buf = ''.join(buf)    
    lr = LoginRequest(buf=buf)
    
    print ('='*80)
    for i in lr.seq:
        print i[0], '\t', lr.__dict__[i[0]]
    
    lr = LoginRequest(length=49)
    lr.deserialize(buf)
    
    print ('='*80)
    for i in lr.seq:
        print i[0], '\t', lr.__dict__[i[0]]
    
    lr.local_port.value = 50009
    lr.local_ip.value = (127, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    lr.password.value = ''.join(reversed(list(lr.password.value)))
    lr.deserialize(lr.serialize().raw)
    
    print ('='*80)
    for i in lr.seq:
        print i[0], '\t', lr.__dict__[i[0]]
    
    print lr.serialize().raw
    print buf
    assert (not lr.serialize().raw == buf)
