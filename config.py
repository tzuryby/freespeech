#!/usr/bin/env python
# -*- coding: UTF-8 -*-


__author__ = 'Tzury Bar Yochay'
__version__ = '0.1'
__license__ = 'GPLv3'

import license
from utils import Storage
from logger import log

#60 Seconds
CLIENT_EXPIRE = 60

RTP_EXPIRE = 20

EMPTY_CTX = (0,) #'\x00'*16

NUM_OF_USERS = license.NUM_OF_USERS
CONCURRENT_SESSIONS = license.CONCURRENT_SESSIONS

Codecs = Storage (
    PCMA='\x01', 
    PCMU='\x02', 
    G723='\x03', 
    ILBC='\x04', 
    SPEEX='\x05', 
    SNAP='\x07',
)

CallTypes = Storage (
    ViaProxy=1, 
    Direct=2,
)

Errors = Storage (
    #general
    Unknown = '\xff\x00',
    UknownClient = '\xff\x01',
    ServerOverloaded = '\xff\x02',
    
    #login
    LoginFailure = '\x01\x01',
    
    #keep-alive
    KeepAlive = '\x02\x02',
    
    #invite
    CalleeNotFound = '\x03\x01',
    CalleeUnavailable = '\x03\x02',
    CodecMismatch = '\x03\x03'
)

ClientStatus = Storage (
    Unknown = '\xff',
    Active = '\x00',
    Busy = '\x01',
    Ringing = '\x02',
    Away = '\x03'
)
    
Listeners = (
    ('udp', 50009),
    ('tcp', 50009),
)
