# -*- coding: utf-8 -*-
'''
Module for managing ceph keys.
'''

from __future__ import absolute_import

# Import python libs
import errno
import re

# Import salt libs
from salt import utils

__virtualname__ = 'ceph_key'

CEPH_CLUSTER_CONNECT_TIMEOUT = 60       # 60 seconds

def __virtual__():
    '''
    Only load if ceph package is installed.

    ceph and other utils are packed in ceph-common package
    '''
    if utils.which('ceph'):
        return __virtualname__
    return False

def create_keyring(name,
                   key,
                   keyring,
                   mon_caps=None,
                   osd_caps=None,
                   mds_caps=None,
                   user='root',
                   group='root',
                   mode='600'):
    # Let's be simple
    if __salt__['file.directory_exists'](keyring):
        return False
    if not __salt__['file.file_exists'](keyring):
        __salt__['file.makedirs'](keyring, user, group, mode)
        __salt__['file.touch'](keyring)

    # Ensure the keyring file's permissions
    __salt__['file.check_perms'](keyring, None, user, group, mode)

    # Construct ceph-authtool cmdline
    cmd = 'ceph-authtool {0} --name {1} --add-key {2}'.format(keyring, name, key)

    if mon_caps:
        cmd += ' --cap mon "{0}"'.format(mon_caps)
    if osd_caps:
        cmd += ' --cap osd "{0}"'.format(osd_caps)
    if mds_caps:
        cmd += ' --cap mds "{0}"'.format(mds_caps)

    # Execute the cmd
    return not __salt__['cmd.retcode'](cmd)

def _check_entity(name,
                  key,
                  admin_name,
                  admin_keyring,
                  cluster,
                  timeout):
    # Construct ceph.conf path
    conf = '/etc/ceph/{0}.conf'.format(cluster)

    # Test if entity exists
    cmd = ['ceph']

    cmd.extend(['--cluster {0}'.format(cluster)])
    cmd.extend(['--conf {0}'.format(conf)])
    cmd.extend(['--connect-timeout {0}'.format(timeout)])
    cmd.extend(['--name {0}'.format(admin_name)])
    cmd.extend(['--keyring {0}'.format(admin_keyring)])
    cmd.extend(['auth get-key'])
    cmd.extend([name])

    ret = __salt__['cmd.run_all'](' '.join(cmd))

    retcode = ret['retcode']

    if retcode:
        return retcode

    # Entity exists then check if key matches
    old_key = ret['stdout']
    rexpr = '^{0}$'.format(key)

    if re.match(rexpr, old_key):
        return 0

    return errno.EEXIST

def register_entity(name,
                    key,
                    admin_name,
                    admin_keyring,
                    mon_caps=None,
                    osd_caps=None,
                    mds_caps=None,
                    cluster='ceph',
                    timeout=CEPH_CLUSTER_CONNECT_TIMEOUT):
    # Construct ceph.conf path
    conf = '/etc/ceph/{0}.conf'.format(cluster)

    retcode = _check_entity(name, key, admin_name, admin_keyring, cluster, timeout)

    if retcode == errno.EEXIST:
        if not unregister_entity(name, admin_name, admin_keyring):
            return False
    elif retcode == errno.ENOENT:
        try:
            # Create a temp keyring
            keyring = utils.mkstemp()

            if not create_keyring(name, key, keyring, mon_caps, osd_caps, mds_caps):
                return False

            # Add entity
            cmd = ['ceph']

            cmd.extend(['--cluster {0}'.format(cluster)])
            cmd.extend(['--conf {0}'.format(conf)])
            cmd.extend(['--connect-timeout {0}'.format(timeout)])
            cmd.extend(['--name {0}'.format(admin_name)])
            cmd.extend(['--keyring {0}'.format(admin_keyring)])
            cmd.extend(['--in-file {0}'.format(keyring)])
            cmd.extend(['auth add'])
            cmd.extend([name])

            if __salt__['cmd.retcode'](' '.join(cmd)):
                return False
            return True
        finally:
            utils.safe_rm(keyring)
    elif retcode:
        return False

    # Update the entity's caps
    caps = []

    if mon_caps:
        caps.extend(['mon "{0}"'.format(mon_caps)])
    if osd_caps:
        caps.extend(['osd "{0}"'.format(osd_caps)])
    if mds_caps:
        caps.extend(['mds "{0}"'.format(mds_caps)])

    if caps:
        cmd = ['ceph']

        cmd.extend(['--cluster {0}'.format(cluster)])
        cmd.extend(['--conf {0}'.format(conf)])
        cmd.extend(['--connect-timeout {0}'.format(timeout)])
        cmd.extend(['--name {0}'.format(admin_name)])
        cmd.extend(['--keyring {0}'.format(admin_keyring)])
        cmd.extend(['auth caps'])
        cmd.extend([name])
        cmd.extend([' '.join(caps)])

        if __salt__['cmd.retcode'](' '.join(cmd)):
            return False

    return True

def unregister_entity(name,
                      admin_name,
                      admin_keyring,
                      cluster='ceph',
                      timeout=CEPH_CLUSTER_CONNECT_TIMEOUT):
    # Construct ceph.conf path
    conf = '/etc/ceph/{0}.conf'.format(cluster)

    # Remove the entity
    cmd = ['ceph']

    cmd.extend(['--cluster {0}'.format(cluster)])
    cmd.extend(['--conf {0}'.format(conf)])
    cmd.extend(['--connect-timeout {0}'.format(timeout)])
    cmd.extend(['--name {0}'.format(admin_name)])
    cmd.extend(['--keyring {0}'.format(admin_keyring)])
    cmd.extend(['auth del'])
    cmd.extend([name])

    return not __salt__['cmd.retcode'](' '.join(cmd))