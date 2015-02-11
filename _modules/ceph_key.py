# -*- coding: utf-8 -*-
'''
Module for managing ceph keys.

author: runsisi@hust.edu.cn
'''

from __future__ import absolute_import

# Import python libs
import errno
from os import path

# Import salt libs
from salt import utils
from salt.exceptions import CommandExecutionError, SaltInvocationError

__virtualname__ = 'ceph_key'

CEPH_CLUSTER = 'ceph'                   # Default cluster name
CEPH_CONF = '/etc/ceph/ceph.conf'       # Default cluster conf file
CEPH_CONNECT_TIMEOUT = 60               # 60 seconds

def __virtual__():
    '''
    Only load if ceph package is installed.

    ceph and other utils are packed in ceph-common package
    '''
    if utils.which('ceph'):
        return __virtualname__
    return False

def _error(ret, msg):
    ret['result'] = False
    ret['comment'] = msg
    return ret

def manage_keyring(keyring,
                   entity_name,
                   entity_key,
                   mon_caps=None,
                   osd_caps=None,
                   mds_caps=None,
                   user='root',
                   group='root',
                   mode='600'):
    keyring = path.expanduser(keyring)
    keyring = path.abspath(keyring)

    ret = {
        'name': keyring,
        'result': True,
        'comment': 'Keyring managed',
        'changes': {}
    }

    # Check keyring file
    try:
        if not path.exists(keyring):
            dirname = path.dirname(keyring)
            basename = path.basename(keyring)

            if not path.exists(dirname):
                __salt__['file.mkdir'](dirname, user, group, mode)
                ret['changes'][dirname] = 'New directory'

            if not __salt__['file.touch'](keyring):
                return _error(ret, 'Create keyring failure')
            ret['changes'][basename] = 'New file'
        else:
            if not __salt__['file.file_exists'](keyring):
                return _error(ret, 'Path already exists and is not a file')

        data, _ = __salt__['file.check_perms'](keyring, None,
                                               user, group, mode, True)

        if not data['result']:
            return _error(ret, data['comment'])
        if data['changes']:
            ret['changes']['perms'] = data['changes']
    except (OSError, CommandExecutionError, SaltInvocationError) as e:
        return _error(ret, '{0}'.format(e))

    # Check entity
    entity = {'key': entity_key}
    if mon_caps:
        entity.update({'caps mon': '"{0}"'.format(mon_caps)})
    if osd_caps:
        entity.update({'caps osd': '"{0}"'.format(osd_caps)})
    if mds_caps:
        entity.update({'caps mds': '"{0}"'.format(mds_caps)})

    fentity = __salt__['ini.get_section'](keyring, entity_name)

    if fentity == entity:
        return ret

    # Update entity
    cmd = ['ceph-authtool']

    cmd.append(keyring)
    cmd.append('--name {0}'.format(entity_name))
    cmd.append('--add-key {0}'.format(entity_key))
    if mon_caps:
        cmd.append('--cap mon "{0}"'.format(mon_caps))
    if osd_caps:
        cmd.append('--cap osd "{0}"'.format(osd_caps))
    if mds_caps:
        cmd.append('--cap mds "{0}"'.format(mds_caps))

    cmd = ' '.join(cmd)

    data = __salt__['cmd.run_all'](cmd)
    if data['retcode']:
        return _error(ret, '{0}'.format(data['stderr']))
    ret['changes']['entity'] = entity

    return ret

def remove_keyring(keyring,
                   name=''):
    # TODO: Support remove a single entity
    keyring = path.expanduser(keyring)
    keyring = path.abspath(keyring)

    ret = {
        'name': keyring,
        'result': True,
        'comment': 'Keyring removed',
        'changes': {}
    }

    if not path.exists(keyring):
        ret['comment'] = 'Keyring does not exist, skip'
        return ret

    if not __salt__['file.file_exists'](keyring):
        return _error(ret, 'Path exists and is not a file')

    result = __salt__['file.remove'](keyring)
    if result:
        ret['changes'][keyring] = 'Removed'
    else:
        return _error(ret, 'Remove keyring failure')

    return ret

def manage_entity(name,
                  entity_key,
                  admin_name,
                  admin_key,
                  mon_caps=None,
                  osd_caps=None,
                  mds_caps=None,
                  cluster=CEPH_CLUSTER,
                  conf=CEPH_CONF):
    ret = {
        'name': name,
        'result': True,
        'comment': 'Entity managed',
        'changes': {}
    }

    cluster, conf = __salt__['ceph_mon.normalize'](cluster, conf)

    try:
        # Create temp admin keyring and keyring
        admin_keyring = utils.mkstemp()
        keyring = utils.mkstemp()

        data = manage_keyring(admin_keyring, admin_name, admin_key)

        if not data['result']:
            return _error(ret, '{0}'.format(data['comment']))

        # Export entity
        cmd = ['ceph']

        cmd.append('--cluster {0}'.format(cluster))
        cmd.append('--conf {0}'.format(conf))
        cmd.append('--connect-timeout {0}'.format(CEPH_CONNECT_TIMEOUT))
        cmd.append('--name {0}'.format(admin_name))
        cmd.append('--keyring {0}'.format(admin_keyring))
        cmd.append('--out-file {0}'.format(keyring))
        cmd.append('auth')
        cmd.append('export')
        cmd.append(name)

        cmd = ' '.join(cmd)

        data = __salt__['cmd.run_all'](cmd)

        if data['retcode'] and data['retcode'] != errno.ENOENT:
            return _error(ret, '{0}'.format(data['stderr']))

        # Entity existed
        fentity = None

        # Entity we wanted
        entity = {'key': entity_key}
        if mon_caps:
            entity.update({'caps mon': '"{0}"'.format(mon_caps)})
        if osd_caps:
            entity.update({'caps osd': '"{0}"'.format(osd_caps)})
        if mds_caps:
            entity.update({'caps mds': '"{0}"'.format(mds_caps)})

        # Entity exists
        if not data['retcode']:
            fentity = __salt__['ini.get_section'](keyring, name)

            if not fentity:
                return _error(ret, 'Read keyring failure')

            if fentity == entity:
                return ret

            # Key matches
            if fentity['key'] == entity['key']:
                caps = []

                if mon_caps:
                    caps.append('mon "{0}"'.format(mon_caps))
                if osd_caps:
                    caps.append('osd "{0}"'.format(osd_caps))
                if mds_caps:
                    caps.append('mds "{0}"'.format(mds_caps))

                caps = ' '.join(caps)

                # ceph auth caps does not support zero caps
                if caps:
                    cmd = ['ceph']

                    cmd.append('--cluster {0}'.format(cluster))
                    cmd.append('--conf {0}'.format(conf))
                    cmd.append('--connect-timeout {0}'.format(CEPH_CONNECT_TIMEOUT))
                    cmd.append('--name {0}'.format(admin_name))
                    cmd.append('--keyring {0}'.format(admin_keyring))
                    cmd.append('auth')
                    cmd.append('caps')
                    cmd.append(name)
                    cmd.append(caps)

                    cmd = ' '.join(cmd)

                    data = __salt__['cmd.run_all'](cmd)

                    if data['retcode']:
                        return _error(ret, '{0}'.format(data['stderr']))

                    ret['changes']['before'] = fentity
                    ret['changes']['after'] = entity

                    return ret

            # Key does not match or zero caps
            cmd = ['ceph']

            cmd.append('--cluster {0}'.format(cluster))
            cmd.append('--conf {0}'.format(conf))
            cmd.append('--connect-timeout {0}'.format(CEPH_CONNECT_TIMEOUT))
            cmd.append('--name {0}'.format(admin_name))
            cmd.append('--keyring {0}'.format(admin_keyring))
            cmd.append('auth')
            cmd.append('del')
            cmd.append(name)

            cmd = ' '.join(cmd)

            data = __salt__['cmd.run_all'](cmd)

            if data['retcode']:
                return _error(ret, '{0}'.format(data['stderr']))

        # Entity does not exist or deleted by us
        data = manage_keyring(keyring, name, entity_key, mon_caps, osd_caps, mds_caps)
        if not data['result']:
            return _error(ret, '{0}'.format(data['comment']))

        # Add new entity
        cmd = ['ceph']

        cmd.append('--cluster {0}'.format(cluster))
        cmd.append('--conf {0}'.format(conf))
        cmd.append('--connect-timeout {0}'.format(CEPH_CONNECT_TIMEOUT))
        cmd.append('--name {0}'.format(admin_name))
        cmd.append('--keyring {0}'.format(admin_keyring))
        cmd.append('--in-file {0}'.format(keyring))
        cmd.append('auth')
        cmd.append('add')
        cmd.append(name)

        cmd = ' '.join(cmd)

        data = __salt__['cmd.run_all'](cmd)

        if data['retcode']:
            return _error(ret, '{0}'.format(data['stderr']))

        ret['changes']['before'] = fentity
        ret['changes']['after'] = entity

        return ret
    finally:
        utils.safe_rm(admin_keyring)
        utils.safe_rm(keyring)

def remove_entity(name,
                  admin_name,
                  admin_key,
                  cluster=CEPH_CLUSTER,
                  conf=CEPH_CONF):
    ret = {
        'name': name,
        'result': True,
        'comment': 'Entity removed',
        'changes': {}
    }

    cluster, conf = __salt__['ceph_mon.normalize'](cluster, conf)

    try:
        # Create temp admin keyring
        admin_keyring = utils.mkstemp()

        data = manage_keyring(admin_keyring, admin_name, admin_key)

        if not data['result']:
            return _error(ret, '{0}'.format(data['comment']))

        # Check entity
        cmd = ['ceph']

        cmd.append('--cluster {0}'.format(cluster))
        cmd.append('--conf {0}'.format(conf))
        cmd.append('--connect-timeout {0}'.format(CEPH_CONNECT_TIMEOUT))
        cmd.append('--name {0}'.format(admin_name))
        cmd.append('--keyring {0}'.format(admin_keyring))
        cmd.append('auth')
        cmd.append('get')
        cmd.append(name)

        cmd = ' '.join(cmd)

        data = __salt__['cmd.run_all'](cmd)

        if data['retcode'] == errno.ENOENT:
            ret['comment'] = 'Entity does not exist, skip'
            return ret

        if data['retcode']:
            return _error(ret, '{0}'.format(data['stderr']))

        # Remove the entity
        cmd = ['ceph']

        cmd.append('--cluster {0}'.format(cluster))
        cmd.append('--conf {0}'.format(conf))
        cmd.append('--connect-timeout {0}'.format(CEPH_CONNECT_TIMEOUT))
        cmd.append('--name {0}'.format(admin_name))
        cmd.append('--keyring {0}'.format(admin_keyring))
        cmd.append('auth')
        cmd.append('del')
        cmd.append(name)

        cmd = ' '.join(cmd)

        data = __salt__['cmd.run_all'](cmd)

        if data['retcode']:
            return _error(ret, '{0}'.format(data['stderr']))

        ret['changes'][name] = 'Removed'

        return ret
    finally:
        utils.safe_rm(admin_keyring)
