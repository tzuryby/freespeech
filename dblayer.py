#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import re
from db import db
from utils import Storage

__all__ = ['Config', 'Users']
    
def config():
    table = Storage()
    for row in db.select('select key, value, fn from config'):
        table[row.key] = eval(row.fn % row.value)
    return table
    
Config = config()

def users():
    users = Storage()
    for row in db.select('select * from users'):
        users[row.username] = row
    return users
    
Users = users()
#Users = Config.Users = users()

if __name__ == '__main__':
    for key in Config.keys():
        print key, Config[key]

    for user in Users:
        print Users[user]
