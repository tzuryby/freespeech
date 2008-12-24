#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import re
from db import db
from utils import Storage
from logger import log

__all__ = ['Config', 'Users']


def users():
    users = Storage()
    for row in db.select('select * from users'):
        users[row.username] = row
    return users
    
Users = users()

if __name__ == '__main__':

    for user in Users:
        print Users[user]
