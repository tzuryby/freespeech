
import struct
import re

from utils import Storage
from ctypes import create_string_buffer

class ByteField(object):
    '''each field within a message has the following properties:
        starting-point, ending-point, length, format, pack, unpack
    '''
    start = 0
    length = 1
    format = '!c'
    _value = None
    
    def __init__(self):
        pass
    
    def end(self):
        return self.start + self.length
    
    def pack_into(self, buf):
        struct.pack_into(self.format, buf, self.start, self.value)
        
    def unpack_from(self, buf):
        self.value = struct.unpack_from(self.format, buf, self.start)
    
    def __setattr__(self, k, v):
        '''a wrapper around x.value'''
        if k == 'value':
            self._value = v
        else:
            self.__dict__[k] = v
        
    def __getattr__(self, k):
        if k == 'value':
            return self._value
        else:
            raise AttributeError

class ShortField(ByteField):
    def __init__(self, start):
        self.start = start
        self.length = 2
        self.format = '!h'

class IntField(ByteField):
    def __init__(self, start):
        self.start = start
        self.length = 4
        self.format = '!i'


class StringField(ByteField):
    def __init__(self, start, format):
        self.format = format
        self.start = start
        self.length = struct.calcsize(self.format)
            
    def pack_into(self, buf):
        struct.pack_into(self.format, buf, self.start, *(self.value))
    
    def unpack_from(self, buf):
        self.value = struct.unpack_from(self.format, buf, self.start)
    
    def __setattr__(self, k, v):
        if k == 'value':
            '''a wrapper around x.value'''
            # if yo uchange the format you must change the len as well.
            self.format = '!%dc' % len(v)
            self.length = struct.calcsize(self.format)
            self._value = type(v) in (list, tuple) and ''.join(v) or v
        else:
            self.__dict__[k] = v
        
    def __getattr__(self, k):
        if k == 'value':
            return (c for c in self._value) #re.findall('.', self._value)
        else:
            raise AttributeError

class LoginRequest(object):    
    def __init__(self, **kwargs):
        self.seq = dict([
            ('0_username_length', (ShortField, 0)), 
            ('1_username', (StringField, 2, lambda: '!%dc' % self.username_length )), 
            ('2_password', (StringField, lambda: self.username.end(), '!20c')), 
            ('3_local_ip', (StringField, lambda: self.password.end(), '!4c')), 
            ('4_local_port', (IntField, lambda: self.local_ip.end()))
        ])
        if 'buf' in kwargs:
            self.buf = buf
            self.deserialize(buf)
        elif 'length' in kwargs:
            self.buf = create_string_buffer(kwargs['length'])
        
        
    def deserialize(self, buf=None):
        if buf:
            self.buf = buf
        for key in sorted(self.seq.keys()):
            params = self.seq[key]
            constructor, start = params[0], params[1]
            format = len(params) == 3 and params[2] or None
            # in case of starting point is a lambda expression
            if hasattr(start, '__call__'):
                start = start()            
            
            self.__dict__[key] = format and params[0](start, format) or params[0](start)
            self.__dict__[key].unpack_from(self.buf)
            
    def serialize(self):
         for key in self.seq.keys():
             self.__dict__[key].pack_into(self.buf)
             
         return self.buf
             
             

    
if __name__ == '__main__':
    buff = '\x08\x71\x72\x73\x74\x75\x76\x77\x78\x72\x73\x74\x75\x76\x77\x78\x79\x69\x68\x67\x66' \
           '\x70\x71\x72\x73\x74\x75\x76\x77\x78\x79\x69\x68\x67\x66' \
           '\x70\x71\x72\x73\x74\x75\x76\x77\x78\x79\x69\x68\x67\x66'
    
    lr = LoginRequest(buff=buff)
    lr.deserialize()

    for d in lr.data:
        print d, ':', hasattr(lr[d], 'value') and lr[d].value or lr[d]
    



