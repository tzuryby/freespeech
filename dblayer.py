#!/usr/bin/env python

import re
from db import db
from utils import Hashtable

__all__ = ['Config']
    
def config():
    table = Hashtable()
    for row in db.select('select key, value, fn from config'):
        table[row.key] = eval(row.fn % row.value)
    return table
    
Config = config()


if __name__ == '__main__':
    for key in Config.keys():
        print key, Config[key]
        
