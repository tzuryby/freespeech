#!/usr/bin/env python
# -*- coding: UTF-8 -*-


__author__ = 'Tzury Bar Yochay'
__version__ = '0.1'
__license__ = 'GPLv3'


__all__ = ['printargs']
from logger import log

def printargs(fn, *args, **kwargs):
    def wrapper(*args, **kwargs):
        print 'function name:', fn.__name__
        print 'args:', args
        print 'kwargs:', kwargs        
        return fn(*args, **kwargs)
    
    return wrapper
    
if __name__ == '__main__':
    @printargs
    def bar(a,b,c, hello='World'):
        print 'Hello ' + hello
        
    bar(1,2,3)
    