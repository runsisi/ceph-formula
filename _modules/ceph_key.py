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

    # Test if entity exists
    cmd = 'ceph --cluster {0} --conf {1} --connect-timeout {2} ' \
          '--name {3} --keyring {4} auth get-key {5}'\
        .format(cluster, conf, timeout, admin_name, admin_keyring, name)
    ret = __salt__['cmd.run_all'](cmd)

    retcode = ret['retcode']

    if retcode and retcode != errno.ENOENT:
        return False

    need_add_entity = True

    # Entity exists
    if not retcode:
        old_key = ret['stdout']
        rexpr = '^{0}$'.format(key)

        if not re.search(rexpr, old_key):
            if not unregister_entity(name, admin_name, admin_keyring):
                return False
        else:
            need_add_entity = False

    keyring = None

    try:
        # Need to add a new entity
        if need_add_entity:
            # Create a temp keyring
            keyring = utils.mkstemp()

            if not create_keyring(name, key, keyring, mon_caps, osd_caps, mds_caps):
                return False

            # Add entity
            cmd = 'ceph --cluster {0} --conf {1} --connect-timeout {2} ' \
                  '--name {3} --keyring {4} --in-file {5} auth add {6}'\
                .format(cluster, conf, timeout, admin_name, admin_keyring, keyring, name)

            if __salt__['cmd.retcode'](cmd):
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
            cmd = 'ceph --cluster {0} --conf {1} --connect-timeout {2} ' \
                  '--name {3} --keyring {4} auth caps {5} {6}'\
                .format(cluster, conf, timeout, admin_name, admin_keyring, name,
                        ' '.join(caps))
            if __salt__['cmd.retcode'](cmd):
                return False
    finally:
        if keyring:
            utils.safe_rm(keyring)

    return True

def unregister_entity(name,
                      admin_name,
                      admin_keyring,
                      cluster='ceph',
                      timeout=CEPH_CLUSTER_CONNECT_TIMEOUT):
    # Construct ceph.conf path
    conf = '/etc/ceph/{0}.conf'.format(cluster)

    # Remove the entity
    cmd = 'ceph --cluster {0} --conf {1} --connect-timeout {2} ' \
          '--name {3} --keyring {4} auth del {5}'.format(
        cluster, conf, timeout, admin_name, admin_keyring, name)

    return not __salt__['cmd.retcode'](cmd)