
__author__ = 'Tzury Bar Yochay'
__version__ = '0.1'
__license__ = 'GPLv3'
__all__ = ['Storage',]

#extending dict with dot notation 'o.key' in addition to 'o[key]'
#~ class Storage(dict):
    #~ def __getattr__(self, key):
        #~ return self[key]
        
    #~ def __setattr__(self, key, value): 
        #~ self[key] = value
        
    #~ def __delattr__(self, key):
        #~ del self[key]
        
class Storage(dict):
    def __new__(cls, *args, **kwargs):
        self = dict.__new__(cls, *args, **kwargs)
        self.__dict__ = self
        return self