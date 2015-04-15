# -*- coding: utf-8 -*-
# runsisi AT hust.edu.cn

import logging
import os
import tempfile
from ..repo import yum_repo
from ..cmd import (run, check_run, CommandExecutionError)

LOG = logging.getLogger(__name__)


def setup_repo(pkgs_dir):
    (fd, path) = tempfile.mkstemp(prefix='clove')
    os.close(fd)

    repo = {
        'reponame': 'clove',
        'name': 'Packages for clove',
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

    repopath = '/etc/yum.repos.d/{0}'.format('clove.repo')

    LOG.debug('Create repo file: {0}'.format(repopath))

    try:
        os.rename(path, repopath)
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


def backup_repo():
    repodir = '/etc/yum.repos.d/'

    for fn in os.listdir(repodir):
        fromfn = os.path.join(repodir, fn)
        tofn = os.path.join(repodir, fn + '.bak')
        os.rename(fromfn, tofn)


def restore_repo(cloverepo):
    repodir = '/etc/yum.repos.d/'

    if os.path.exists(cloverepo):
        os.remove(cloverepo)

    for fn in os.listdir(repodir):
        fromfn = os.path.join(repodir, fn)
        tofn = os.path.join(repodir, fn[:-4])
        os.rename(fromfn, tofn)
