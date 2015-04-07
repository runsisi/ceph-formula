# -*- coding: utf-8 -*-
# runsisi AT hust.edu.cn

import ConfigParser
import logging

LOG = logging.getLogger(__name__)


class _IniFile(object):
    '''
    ConfigParser module of python 2.x does not support leading space
    in the ini file, so feed this to ConfigParser
    '''
    def __init__(self, fpath, write=False):
        super(_IniFile, self).__init__()
        self.fpath = fpath
        self.mode = 'rb'
        if write:
            self.mode = 'rwb'

    def __enter__(self):
        try:
            self.fobj = open(self.fpath, self.mode)
        except IOError as e:
            LOG.warning(e)
            self.fobj = None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.fobj is not None:
            self.fobj.close()
        return False

    def readline(self):
        line = self.fobj.readline()

        return line.lstrip(' \t')


class Cfg(object):
    def __init__(self, conf):
        super(Cfg, self).__init__()

        self.conf = conf
        self.parser = ConfigParser.SafeConfigParser()

    def open(self, write=False):
        with _IniFile(self.conf, write) as ini:
            if ini.fobj is None:
                return None
            self.parser.readfp(ini)
            return self.parser

    def write(self):
        with open(self.conf, 'wb') as fobj:
            self.parser.write(fobj)
