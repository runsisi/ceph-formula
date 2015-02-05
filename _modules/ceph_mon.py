# -*- coding: utf-8 -*-
'''
Module for managing ceph MONs.
'''

from __future__ import absolute_import

# Import python libs
import errno
import re
from os import path, listdir

# Import salt libs
from salt import utils

__virtualname__ = 'ceph_mon'

DONE_FILE_NAME = 'sysvinit'
DONE_FILE_MAGIC = '\xc3\xc3\xc8\xfd'
CEPH_CLUSTER_CONNECT_TIMEOUT = 60       # 60 seconds

def __virtual__():
    '''
    Only load if ceph package is installed.

    ceph and other utils are packed in ceph-common package
    ceph-mon, ceph-osd etc. are packed in ceph package
    '''
    if utils.which('ceph') and utils.which('ceph-mon'):
        return __virtualname__
    return False

def _check_monfs(mon_id,
                 mon_data,
                 mon_addr,
                 auth_type,
                 mon_key):
    if not listdir(mon_data):
        return errno.ENOENT

    done_file_path = mon_data + DONE_FILE_NAME

    if not __salt__['file.file_exists'](done_file_path):
        return errno.EEXIST

    lines = ['magic={0}'.format(DONE_FILE_MAGIC),
             'mon_id={0}'.format(mon_id),
             'mon_addr={0}'.format(mon_addr if mon_addr else 'None'),
             'auth_type={0}'.format(auth_type),
             'mon_key={0}'.format(mon_key if mon_key else 'None')]

    try:
        with utils.fopen(done_file_path, 'r') as done_file:
            lineno = 0
            for line in done_file:
                if not re.match(lines[lineno], line) or lineno == len(lines):
                    return errno.EEXIST
                lineno += 1
    except:
        return errno.EEXIST
    return 0

def _tag_monfs(mon_id,
               mon_data,
               mon_addr,
               auth_type,
               mon_key):
    done_file_path = mon_data + DONE_FILE_NAME

    lines = ['magic={0}'.format(DONE_FILE_MAGIC),
             'mon_id={0}'.format(mon_id),
             'mon_addr={0}'.format(mon_addr if mon_addr else 'None'),
             'auth_type={0}'.format(auth_type),
             'mon_key={0}'.format(mon_key if mon_key else 'None')]

    try:
        __salt__['file.write'](done_file_path, args=lines)
    except:
        __salt__['file.remove'](done_file_path)
        return False
    return True

def _create_monfs(mon_id,
                  mon_data,
                  mon_addr,
                  auth_type,
                  mon_key,
                  cluster):
    # Construct ceph.conf path
    conf = '/etc/ceph/{0}.conf'.format(cluster)

    # TODO: What should we do if the path is a symbolic file that
    # links to a directory?
    if __salt__['file.file_exists'](path.dirname(mon_data)):
        return False

    # Create mon_data directory or clean it
    if not __salt__['file.directory_exists'](mon_data):
        __salt__['file.makedirs'](mon_data)
    else:
        retcode = _check_monfs(mon_id, mon_data, mon_addr, auth_type, mon_key)

        if not retcode:
            return True
        elif retcode == errno.EEXIST:
            cmd = ['rm -rf']
            cmd.extend(['{0}*'.format(mon_data)])
            __salt__['cmd.run'](' '.join(cmd))
        elif retcode != errno.ENOENT:
            return False

    keyring = ''

    # Create temp mon keyring
    if auth_type == 'cephx' and mon_key:
        keyring = utils.mkstemp()
        if not __salt__['ceph_key.create_keyring']('mon.', mon_key, keyring,
                                                   mon_caps='allow *'):
            return False

    # Do the real job
    cmd = ['ceph-mon']

    cmd.extend(['--cluster {0}'.format(cluster)])
    cmd.extend(['--conf {0}'.format(conf)])
    cmd.extend(['--id {0}'.format(mon_id)])
    cmd.extend(['--mkfs'])

    if keyring:
        cmd.extend(['--keyring {0}'.format(keyring)])
    if mon_addr:
        cmd.extend(['--public-addr {0}'.format(mon_addr)])
    try:
        if __salt__['cmd.retcode'](' '.join(cmd)):
            return False
    finally:
        utils.safe_rm(keyring)

    # Create permanent mon keyring
    if auth_type == 'cephx' and mon_key:
        keyring = mon_data + keyring
        if not __salt__['ceph_key.create_keyring']('mon.', mon_key, keyring,
                                                   mon_caps='allow *'):
            return False

    # Create a magic file to prevent the next try
    if not _tag_monfs(mon_id, mon_data, mon_addr, auth_type, mon_key):
        return False

    return True

def create_mon(mon_id,
               mon_data='',
               mon_addr='',
               auth_type='cephx',
               mon_key='',
               admin_key='',
               cluster='ceph'):
    # Normalize mon_data directory
    if mon_data:
        if not mon_data.endswith('/'):
            mon_data += '/'
    else:
        mon_data = '/var/lib/ceph/mon/{0}-{1}/'.format(cluster, mon_id)

    # Create mon fs
    if not _create_monfs(mon_id, mon_data, mon_addr, auth_type, mon_key, cluster):
        return False

    # Register client.admin auth info
    keyring = mon_data + 'keyring'

    if auth_type == 'cephx' and admin_key:
        if not __salt__['ceph_key.register_entity']('client.admin', admin_key,
                                                    'mon.', keyring,
                                                    'allow *', 'allow *', 'allow',
                                                    cluster):
            return False

    return True