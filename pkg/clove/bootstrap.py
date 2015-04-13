#!/usr/bin/env python
# -*- coding: utf-8 -*-
# runsisi AT hust.edu.cn

from __future__ import absolute_import

import os
import sys
import logging
import logging.handlers
import argparse

CLOVE_DIR = os.path.dirname(__file__)
sys.path.append(CLOVE_DIR)
import utils.log as clovelog
import utils.deploy as clovedeploy

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

    if args.verbose is None:
        args.verbose = 1

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

    LOG.debug('Setup clove pkgs')
    if not clovedeploy.setup_pkgs(CLOVE_DIR):
        LOG.error('setup_pkgs failed')
        return 1

    LOG.debug('Post install process')
    if not post_install():
        LOG.error('post_install failed')
        return 1

    return 0


def parse_args():
    parser = argparse.ArgumentParser('clove-deploy')
    parser.add_argument(
        '-v', '--verbose',
        action='count', default=None,
        help='be more verbose'
    )

    return parser.parse_args()


def post_install():
    LOG.debug('Setup salt environment')

    if not clovedeploy.setup_salt():
        LOG.error('setup_salt failed')
        return False

    notes = '''
1) Define "/etc/salt/roster" before deploy salt minions, refer
   to "/etc/clove_deploy/examples/etc/roster" as an example.
2) Please modify config file "/etc/clove_deploy/clove.sls" to
   fit your cluster.
   '''
    print(notes)

    return True


if __name__ == '__main__':
    ret = main()
    if ret:
        LOG.fatal('Bootstrap failed, see {0} for more details'
                  .format('/var/log/clove_deploy.log'))
    sys.exit(ret)
