#!/usr/bin/env python
# -*- coding: UTF-8 -*-

'''
    **************************************
    Database connectivity layer (part of freespeech.py)
    **************************************
'''
__all__ = ['db']

import sqlite3
from utils import Storage

class _db(object):
    def __init__(self):
        self.dbname = '.freespeech.db'
        self.conn = None
        
    def connect(self, to=None):
        try:
            self.conn = sqlite3.connect(to or self.dbname)
        except:
            raise 'error connecting to db %s' % self.dbname
            
    def cursor(self):
        self.connect()
        return self.conn.cursor()
        
    def close(self):
        self.conn and self.conn.close()
        self.conn = None
        
    def insert(self, table, **kwargs):
        sql = 'INSERT INTO %s (%s) VALUES (%s)' % (table, 
            ', '.join(kwargs.keys()),
            ', '.join([self.sqlquote(v) for v in kwargs.values()]))
        self.execute(sql)
        
    def delete(self, table, where='1=0'):
        sql = "DELETE FROM %s" % table
        if where:
            sql += " WHERE %s" % where
        self.execute(sql)
        
    def select(self, query):
        try:
            cur = self.cursor()
            cur.execute(query)
            names = [x[0] for x in cur.description]
            row = cur.fetchone()
            while row:
                yield Storage(dict(zip(names, row)))
                row = cur.fetchone()
            self.close()
        except:
            print 'db select error'
        finally:
            self.close()
            
    def sqlquote(self, v):
        if (isinstance(v, (int, float))):
            return str(v)
        return '"%s"' % v
        
    def execute(self, sql):
        self.connect()
        self.conn.execute(sql)
        self.conn.commit()
        self.close()
        
    def update(self, table, **kwargs):        
        _update = 'UPDATE %s ' % table
        _set = ' SET ' + ', '.join([k + '=' + self.sqlquote(v) for k,v in kwargs.iteritems() if k != 'where'])
        _where = ('where' in kwargs and ' WHERE %s ' % kwargs['where']) or ''
        self.execute(_update + _set + _where)
        
db = _db()