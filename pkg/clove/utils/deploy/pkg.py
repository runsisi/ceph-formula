# -*- coding: utf-8 -*-
# runsisi AT hust.edu.cn

import logging
import os
import tempfile
import shutil
from ..repo import yum_repo
from ..cmd import (run, check_run, CommandExecutionError)

LOG = logging.getLogger(__name__)


def setup_repo(pkgs_dir):
    (fd, path) = tempfile.mkstemp(prefix='clove')
    os.close(fd)

    repo = {
        'reponame': 'clove-deploy',
        'name': 'Packages for clove-deploy',
        'baseurl': 'file://{0}'.format(pkgs_dir),
        'gpgcheck': 0
    }

    content = yum_repo(**repo)

    LOG.info('Write repo content: {0}'.format(content))

    try:
        with open(path, 'wb') as fobj:
            fobj.write(content)
            os.fsync(fobj.fileno())
    except IOError as e:
        LOG.warning(e)
        return ''

    repopath = '/etc/yum.repos.d/{0}'.format('clove-deploy.repo')

    LOG.debug('Create repo file: {0}'.format(repopath))

    try:
        shutil.move(path, repopath)
    except OSError as e:
        LOG.warning(e)
        os.remove(path)
        return ''

    return repopath


def install_pkgs(pkgs, timeout):
    if isinstance(pkgs, str):
        pkgs = [pkgs]

    LOG.debug('Try to kill running yum instance')

    # kill running instance
    cmd = ['pkill']
    cmd.append('-9')
    cmd.append('yum')

    run(cmd)

    LOG.debug('yum clean all before installing packages')
    cmd = ['yum']
    cmd.append('clean')
    cmd.append('all')

    run(cmd)

    LOG.debug('Install pkgs: {0}'.format(pkgs))

    for pkg in pkgs:
        cmd = ['yum']
        cmd.append('--disablerepo={0}'.format('*'))
        cmd.append('--enablerepo={0}'.format('clove-deploy'))
        cmd.append('-y')
        cmd.append('install')
        cmd.append(pkg)

        try:
            check_run(cmd, timeout)
        except CommandExecutionError as e:
            LOG.warning('Failed to install pkg: {0}\nReason: {1}'.format(pkg, e))
            return False

    LOG.debug('yum clean all after packages installed')
    cmd = ['yum']
    cmd.append('clean')
    cmd.append('all')

    run(cmd)

    return True


def remove_repo(cloverepo):
    if os.path.exists(cloverepo):
        os.remove(cloverepo)
