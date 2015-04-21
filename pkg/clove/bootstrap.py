#!/usr/bin/env python
# -*- coding: utf-8 -*-
# runsisi AT hust.edu.cn

from __future__ import absolute_import

import os
import sys
import logging
import logging.handlers
import shlex

CLOVE_DIR = os.path.dirname(__file__)
sys.path.append(CLOVE_DIR)
import utils.log as clog
import utils.deploy as cdeploy
import utils.cmd as ccmd
import utils.distro as cdistro

LOG = logging.getLogger('bootstrap')


def main():
    # setup logger
    sh = logging.StreamHandler()
    sh.setFormatter(clog.color_format())
    sh.setLevel(logging.DEBUG)

    fh = logging.handlers.RotatingFileHandler('/var/log/clove_deploy.log',
                                              maxBytes=1 << 20, backupCount=3)
    fh.setFormatter(logging.Formatter(clog.BASE_FORMAT))
    fh.setLevel(logging.DEBUG)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(sh)
    logger.addHandler(fh)

    # detect distribution info
    distro = cdistro.distribution_information()
    if distro.name not in ('redhat', 'centos'):
        LOG.error('Not supported distribution')
        return 1

    try:
        import argparse
    except ImportError:
        pkgs_dir = os.path.join(CLOVE_DIR, 'pkgs-el{0}'.format(distro.major))

        cmd = ['rpm']
        cmd.append('-Uvh')
        cmd.append(os.path.join(pkgs_dir, 'python-argparse-*'))

        try:
            ccmd.check_run(cmd)
        except ccmd.CommandExecutionError as e:
            LOG.warning(e)
            return 1

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

    # reset logging level
    verbose = min(args.verbose, len(levels) - 1)
    level = levels[verbose]
    sh.setLevel(level)

    LOG.debug('Setup clove pkgs')
    if not cdeploy.setup_pkgs(CLOVE_DIR):
        LOG.error('setup_pkgs failed')
        return 1

    LOG.debug('Setup salt: stop firewall etc.')
    if not setup_salt():
        LOG.error('setup_salt failed')
        return 1

    return 0


def parse_args():
    import argparse

    parser = argparse.ArgumentParser('clove-deploy')
    parser.add_argument(
        '-v', '--verbose',
        action='count', default=None,
        help='be more verbose'
    )

    return parser.parse_args()


def setup_salt():
    LOG.debug('Setup salt environment')

    distro = cdistro.distribution_information()

    # TODO: support other distros
    # TODO: check 'init' or 'systemd'
    # TODO: open ports instead of shutdown firewall

    if distro.name in ('redhat', 'centos'):
        if distro.major == '7':
            try:
                # TODO: check 'iptables'?
                LOG.debug('Stop system firewall')

                cmd = 'systemctl disable firewalld'
                cmd = shlex.split(cmd)

                ccmd.check_run(cmd)

                LOG.debug('Enable salt service')

                cmd = 'systemctl stop firewalld'
                cmd = shlex.split(cmd)

                ccmd.check_run(cmd)

                cmd = 'systemctl enable salt-master'
                cmd = shlex.split(cmd)

                ccmd.check_run(cmd)

                cmd = 'systemctl restart salt-master'
                cmd = shlex.split(cmd)

                ccmd.check_run(cmd)
            except ccmd.CommandExecutionError as e:
                LOG.warning(e)
                return False
        else:
            try:
                LOG.debug('Stop system firewall')

                cmd = 'chkconfig iptables off'
                cmd = shlex.split(cmd)

                ccmd.check_run(cmd)

                cmd = 'service iptables stop'
                cmd = shlex.split(cmd)

                ccmd.check_run(cmd)

                LOG.debug('Enable salt service')

                cmd = 'chkconfig salt-master on'
                cmd = shlex.split(cmd)

                ccmd.check_run(cmd)

                cmd = 'service salt-master restart'
                cmd = shlex.split(cmd)

                ccmd.check_run(cmd)
            except ccmd.CommandExecutionError as e:
                LOG.warning(e)
                return False
    else:
        LOG.error('Not supported distro: {0}'.format(distro.distro))
        return False

    notes = '''
1) Define "/etc/salt/roster" before deploying salt minions, refer
   to "/etc/salt/roster" as an example.
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
