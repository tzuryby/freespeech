#!/usr/bin/env python
# -*- coding: UTF-8 -*-

__author__ = 'Tzury Bar Yochay'
__version__ = '0.1'
__license__ = 'GPLv3'

import logging
from logging import handlers
from theme import default_theme as theme

__all__ = ['log', 'cdr_logger']


'''
levels: 'NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
CRITICAL    50
ERROR       40
WARNING     30
INFO        20
DEBUG       10
NOTSET      0
'''

class Logger:    
    def __init__(self):
        self.file_frmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.stream_frmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        self.logger = logging.getLogger('snoip.freespeech')
        self.logger.setLevel(logging.INFO)
        
        # file handler
        self.fh = logging.FileHandler('snoip.freespeech.log')
        
        # stream handler
        self.ch = logging.StreamHandler()
        
        self.ch.setFormatter(self.stream_frmt)
        self.fh.setFormatter(self.file_frmt)
        
        self.logger.addHandler(self.ch)
        self.logger.addHandler(self.fh)
        
    def debug(self, *args):
        self.logger.debug(theme.style_prompt + ''.join(str(i) for i in args) + theme.style_normal)

    def info(self, *args):
        self.logger.info(theme.style_yellow + ''.join(str(i) for i in args) + theme.style_normal)

    def exception(self, *args):
        self.logger.exception(theme.style_fail + ''.join(str(i) for i in args) + theme.style_normal)

    def warning(self, *args):
        self.logger.warning(theme.style_right + ''.join(str(i) for i in args) + theme.style_normal)


class CDRLogger:
    def __init__(self):
        self.file_frmt = logging.Formatter('%(asctime)s,%(message)s')
        self.file_handler = logging.handlers.TimedRotatingFileHandler('cdr.log', 'D')
        self.file_handler.setFormatter(self.file_frmt)
        
        self.logger = logging.getLogger('snoip.freespeech.cdr')
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.file_handler)
        
        
    def writeline(self, rec):
        record = ','.join(map(str, (rec.caller_ctx, rec.callee_ctx, rec.start_time, rec.answer_time, rec.end_time)))
        self.logger.debug(record)
         
log = Logger()
cdr_logger = CDRLogger()