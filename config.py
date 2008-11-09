
from utils import Storage

#60 Seconds
CLIENT_EXPIRE = 60

Codecs = Storage(PCMA='\x01', PCMU='\x02', G723='\x03', ILBC='\x04', SPEEX='\x05', SNAP='\x07')

CallTypes = Storage (ViaProxy=1, Direct=2)

Errors = Storage(
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

ClientStatus = Storage(
    Unknown = '\xff',
    Active = '\x00',
    Busy = '\x01',
    Ringing = '\x02',
    Away = '\x03'
)
    
Listeners = (
    ('udp', 'localhost', 50009),
    ('tcp', 'localhost', 50009),
)


binascii_pipe = False

import binascii
hexlify = lambda data: binascii_pipe and binascii.hexlify(data) or data
unhexlify = lambda data: binascii_pipe and binascii.unhexlify(data) or data