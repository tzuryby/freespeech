#!/usr/bin/env python
# -*- coding: UTF-8 -*-

''' fields that construct a message '''

__all__ = [
    'Field',
    'ByteField',
    'CharField',
    'ShortField',
    'IntField',
    'StringField',
    'UUIDField',
    'IPField',
]

import struct
   
class Field(object):
    def __init__(self, start, format, name=None):
        self._value = None      # value of the field
        self.start = start      # starting position on the buffer
        self.format = format    # pack/unpack format
        self.length = struct.calcsize(self.format)
        self.end = self.start + self.length
        self.name = name
        
    def pack_into(self, buf):
        '''packs the value into a supplied buffer'''
        try:
            struct.pack_into(self.format, buf, self.start, *self._value)
        except Exception, inst:
            log.exception('exception')
            
    def unpack_from(self, buf):
        try:
            '''unpack the value from a supplied buffer'''
            self.value = struct.unpack_from(self.format, buf, self.start)
        except Exception, inst:
            log.exception('exception')
            
    def __setattr__(self, k, v):
        '''a wrapper around x.value ensure _value will always be a tuple'''
        if k == 'value':
            self._value = isinstance(v, tuple) and v or (v,)
        else:
            self.__dict__[k] = v
            
    def __getattr__(self, k):
        '''for single value return tuple[0], otherwise, return the tuple'''
        if k == 'value':
            return len(self._value) == 1 and self._value[0] or self._value
        else:
            raise AttributeError
            
    def __repr__(self):
        '''string representation of the tuple'''
        return self._value
        
class ByteField(Field):
    '''single byte numeric field'''
    def __init__(self, start, name=None):
        Field.__init__(self, start, '!b', name)
        
class CharField(Field):
    '''single byte text field'''
    def __init__(self, start, name=None):
        Field.__init__(self, start, '!c', name)
        
class ShortField(Field):
    '''2 bytes numeric field'''
    def __init__(self, start, name=None):
        Field.__init__(self, start, '!h', name)
        
class IntField(Field):
    '''4 bytes numeric field'''
    def __init__(self, start, name=None):
        Field.__init__(self, start, '!i', name)
        
class StringField(Field):
    '''variable length string'''
    def __init__(self, start, format, name=None):
        try:
            Field.__init__(self, start, format, name)
        except:
            log.exception('exception')
            #print 'error@StringField.__init__\nstart %s, format %s, name %s' % (
            #    start, format, name)
            
    def __setattr__(self, k, v):
        try:
            if k == 'value':
                '''a wrapper around x.value'''
                # if you change the format you must change the length as well.
                self.format = '!%dc' % len(v)
                self.length = struct.calcsize(self.format)
                self._value = ''.join(v)
            else:
                self.__dict__[k] = v
        except:
            log.exception('exception')
            #print 'error@StringField.__setattr__\nname %s, k %s,v %s, format %s, length %s' % (
            #    self.name, k, v, self.format, self.length)
            
    def __getattr__(self, k):
        if k == 'value':
            return self._value[0:]
        else:
            raise AttributeError
            
class UUIDField(StringField):
    '''16 bytes uniqueue_id'''
    def __init__(self, start, name=None):
        StringField.__init__(self, start, '!16c', name)
        
class IPField(Field):
    '''16 bytes for IPv6, in IPv4 only the first 4 bytes are used'''
    def __init__(self, start, name=None):
        Field.__init__(self, start, '!16b', name)
        
    def __setattr__(self, k, v):
        '''a wrapper around x.value'''
        if k == 'value':
            if type(v).__name__ == 'str':
                v = [int(o) 
                    for o in v.split('.')] + [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0] # 4+12
                self._value = v
            else:
                self._value = v
        else:
            self.__dict__[k] = v
