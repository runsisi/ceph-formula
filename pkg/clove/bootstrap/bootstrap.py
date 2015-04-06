#!/usr/bin/env python
# -*- coding: utf-8 -*-

# runsisi AT hust.edu.cn

from __future__ import absolute_import

import os
import sys
import logging
import logging.handlers
import argparse

BOOTSTRAP_DIR = os.path.dirname(__file__)
sys.path.append(BOOTSTRAP_DIR)
import clove.util.log as clovelog
import clove.deploy as clovedeploy

LOG = logging.getLogger('bootstrap')


def main():
    args = parse_args()

    levels = {
        0: logging.FATAL,
        1: logging.ERROR,
        2: logging.WARNING,
        3: logging.INFO,
        4: logging.DEBUG
    }

    verbose = min(args.verbose, len(levels) - 1)
    level = levels[verbose]

    # setup logger

    sh = logging.StreamHandler()
    sh.setFormatter(clovelog.color_format())
    sh.setLevel(level)

    fh = logging.handlers.RotatingFileHandler('/var/log/clove_deploy.log',
                                              maxBytes=1 << 22, backupCount=3)
    fh.setFormatter(logging.Formatter(clovelog.BASE_FORMAT))
    fh.setLevel(logging.DEBUG)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(sh)
    logger.addHandler(fh)

    clove_dir = os.path.abspath(os.path.join(BOOTSTRAP_DIR, '../'))

    LOG.debug('Setup clove deploy')
    if not clovedeploy.setup_deploy(clove_dir):
        LOG.error('Call setup_deploy failed')
        return 1

    return 0


def parse_args():
    parser = argparse.ArgumentParser('clove-deploy')
    parser.add_argument(
        '-v', '--verbose',
        action='count', default=0,
        help='be more verbose'
    )

    return parser.parse_args()


if __name__ == '__main__':
    sys.exit(main())
