#!/usr/bin/env python
# -*- coding: UTF-8 -*-

__author__ = 'Tzury Bar Yochay'
__version__ = '0.1'
__license__ = 'GPLv3'

import logging
from logging import handlers
from theme import default_theme as theme

__all__ = ['log']


'''
levels: 'NOSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'

CRITICAL    50
ERROR       40
WARNING     30
INFO        20
DEBUG       10
NOTSET      0

'''

class Logger:    
    def __init__(self):
        
        self.file_frmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.stream_frmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        #self.socket_frmt = logging.Formatter('%(message)s')
        
        self.logger = logging.getLogger('snoip.freespeech')
        self.logger.setLevel(logging.DEBUG)
        
        # file handler
        self.fh = logging.FileHandler('snoip.freespeech.log')
        
        # stream handler
        self.ch = logging.StreamHandler()
        
        # tcp socket handler
        #self.sh = logging.handlers.SocketHandler('localhost', logging.handlers.DEFAULT_TCP_LOGGING_PORT)
        
        self.ch.setFormatter(self.stream_frmt)
        self.fh.setFormatter(self.file_frmt)
        #self.sh.setFormatter(self.socket_frmt)
        
        self.logger.addHandler(self.ch)
        self.logger.addHandler(self.fh)
        #self.logger.addHandler(self.sh)
        
    def debug(self, *args):
        self.logger.debug(theme.style_field_name + ''.join(str(i) for i in args) + theme.style_normal)

    def info(self, *args):
        self.logger.info(theme.style_yellow + ''.join(str(i) for i in args) + theme.style_normal)

    def exception(self, *args):
        self.logger.exception(theme.style_fail + ''.join(str(i) for i in args) + theme.style_normal)

    def warning(self, *args):
        self.logger.warning(theme.style_class_name + ''.join(str(i) for i in args) + theme.style_normal)

log = Logger()
