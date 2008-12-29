import logging
from logging import handlers

__all__ = ['log']


# levels: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'

class Logger:
    
    def __init__(self):
                
        self.file_frmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.stream_frmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        self.logger = logging.getLogger('snoip.freespeech')
        self.logger.setLevel(logging.DEBUG)
        
        #   file handler
        self.fh = logging.FileHandler('snoip.freespeech.log')
        self.fh.setLevel(logging.DEBUG)
        
        #   stream handler
        self.ch = logging.StreamHandler()
        self.ch.setLevel(logging.DEBUG)
        
        self.ch.setFormatter(self.stream_frmt)
        self.fh.setFormatter(self.file_frmt)
        
        self.logger.addHandler(self.ch)
        self.logger.addHandler(self.fh)
        
        
    def debug(self, *args):
        self.logger.debug(''.join(str(i) for i in args))

    def info(self, *args):
        self.logger.info(''.join(str(i) for i in args))

    def exception(self, *args):
        self.logger.exception(''.join(str(i) for i in args))

    def warning(self, *args):
        self.logger.warning(''.join(str(i) for i in args))


log = Logger()