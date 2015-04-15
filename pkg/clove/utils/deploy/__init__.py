# -*- coding: utf-8 -*-
# runsisi AT hust.edu.cn

import os
import ConfigParser
import logging
from ..cfg import Cfg
from ..cmd import (check_run, CommandExecutionError)
from ..distro import distribution_information
from .pkg import (backup_repo, setup_repo, restore_repo, install_pkgs)

LOG = logging.getLogger(__name__)


def setup_pkgs(clove_dir):
    # gen packages dir
    distro = distribution_information()
    if distro.name in ('redhat', 'centos'):
        pkgs_dir = os.path.join(clove_dir, 'pkgs-el{0}'.format(distro.major))
    else:
        LOG.error('Not supported distribution')
        return False

    conf = os.path.join(clove_dir, 'clove.ini')

    # get package list to install
    cfg = Cfg(conf)
    parser = cfg.open()
    if parser is None:
        LOG.error('clove.ini is missing?')
        return False
    try:
        pkgs = parser.get('deploy', 'pkgs')
        timeout = parser.get('deploy', 'timeout')
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError) as e:
        LOG.error(e)
        return False

    timeout = float(timeout)
    pkgs = [x.strip() for x in pkgs.split(',')]

    if not pkgs[-1]:
        pkgs = pkgs[:-1]
    LOG.info('Got package list to install: {0}'.format(pkgs))

    LOG.debug('Backup yum repo')
    backup_repo()

    path = ''
    try:
        LOG.debug('Setup clove yum repo')
        path = setup_repo(pkgs_dir)
        if not path:
            LOG.warning('Call setup_repo failed')
            return False

        LOG.debug('Install clove pkgs: {0}'.format(pkgs))
        if not install_pkgs(pkgs, timeout):
            LOG.warning('Call install_pkgs failed, pkgs: {0}'
                        .format(pkgs))
            return False
    finally:
        LOG.debug('Restore yum repo')
        restore_repo(path)

    # install ceph-formula
    LOG.debug('Install ceph-formula')

    formula_dir = os.path.join(clove_dir, 'ceph-formula')
    installer = os.path.join(formula_dir, 'install.sh')

    cmd = ['/bin/sh']
    cmd.append(installer)

    LOG.debug('Call ceph-formula installer')
    try:
        check_run(cmd)
    except CommandExecutionError as e:
        LOG.warning('Execute ceph-formula installer failed: {0}'.format(e))
        return False

    return True
