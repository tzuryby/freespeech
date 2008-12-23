import logging as lg

__all__ = ['log']


# levels: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'

class Logger:
    
    def __init__(self):
                
        self.file_frmt = lg.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.stream_frmt = lg.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        self.logger = lg.getLogger('snoip.freespeech')
        self.logger.setLevel(lg.DEBUG)
        
        #   file handler
        self.fh = lg.FileHandler('snoip.freespeech.log')
        self.fh.setLevel(lg.DEBUG)
        
        #   stream handler
        self.ch = lg.StreamHandler()
        self.ch.setLevel(lg.DEBUG)
        
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