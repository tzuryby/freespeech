#!/usr/bin/env python
# -*- coding: UTF-8 -*-


__author__ = 'Tzury Bar Yochay'
__version__ = '0.1'
__license__ = 'GPLv3'


import re
import config
from db import db
from utils import Storage
from logger import log

__all__ = [
    'Users',
]

def users():
    users = Storage()
    for row in db.select('select * from users limit %d' % (config.NUM_OF_USERS)):
        users[row.username] = row
    return users
    
Users = users()

if __name__ == '__main__':
    for user in Users:
        print Users[user]
