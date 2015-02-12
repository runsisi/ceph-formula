# -*- coding: utf-8 -*-
'''
Module for managing ceph MONs.

author: runsisi@hust.edu.cn
'''

from __future__ import absolute_import

# Import python libs
from os import path, listdir

# Import salt libs
from salt import utils

__virtualname__ = 'ceph_mon'

CEPH_CLUSTER = 'ceph'                   # Default cluster name
CEPH_CONF = '/etc/ceph/ceph.conf'       # Default cluster conf file

TAG_FILE_NAME = 'sysvinit'
TAG_FILE_VERSION = 'v0.1'
TAG_FILE_MAGIC = '\xc3\xc3\xc8\xfd'

def __virtual__():
    '''
    Only load if ceph package is installed.

    ceph and other utils are packed in ceph-common package
    ceph-mon, ceph-osd etc. are packed in ceph package
    '''
    if utils.which('ceph') and utils.which('ceph-mon'):
        return __virtualname__
    return False

def _error(ret, msg):
    ret['result'] = False
    ret['comment'] = msg
    return ret

def _tag_file_content(cluster,
                      mon_id,
                      auth_type,
                      mon_key,
                      mon_addr):
    lines = ['magic={0}'.format(TAG_FILE_MAGIC),
             'version={0}'.format(TAG_FILE_VERSION),
             'cluster={0}'.format(cluster),
             'mon_id={0}'.format(mon_id),
             'auth_type={0}'.format(auth_type or 'None'),
             'mon_key={0}'.format(mon_key or 'None'),
             'mon_addr={0}'.format(mon_addr or 'None')]

    return lines

def _file_content_cmp(file_path,
                      content):
    with utils.flopen(file_path, 'r') as fcontent:
        lineno = 0
        for line in fcontent:
            if line.strip() != content[lineno] or lineno == len(content):
                return False
            lineno += 1

    return True

def _mon_data(cluster,
              conf,
              mon_id):
    cmd = ['ceph-mon']

    cmd.append('--cluster {0}'.format(cluster))
    cmd.append('--conf {0}'.format(conf))
    cmd.append('--id {0}'.format(mon_id))
    cmd.append('--show-config-value')
    cmd.append('mon_data')

    return __salt__['cmd.run_stdout'](' '.join(cmd))

def _monfs_finalize(cluster,
                    conf,
                    mon_id,
                    auth_type,
                    mon_key,
                    mon_addr):
    mon_data = _mon_data(cluster, conf, mon_id)

    file_path = '{0}/{1}'.format(mon_data, TAG_FILE_NAME)

    content = _tag_file_content(cluster, mon_id, auth_type, mon_key, mon_addr)

    try:
        __salt__['file.write'](file_path, args=content)
    except IOError:
        return False

    return True

def normalize(cluster,
              conf):
    cluster = cluster.strip()
    conf = conf.strip()

    if not cluster and not conf:
        return CEPH_CLUSTER, CEPH_CONF

    if not cluster:
        cluster = conf.split('/')[-1].split('.')[0]
    elif not conf:
        conf = '{0}/{1}.conf'.format('/etc/ceph', cluster)

    return cluster, conf

def manage_monfs(mon_id,
                 auth_type='none',
                 mon_key='',
                 mon_addr='',
                 cluster=CEPH_CLUSTER,
                 conf=CEPH_CONF):
    ret = {
        'name': mon_id,
        'result': True,
        'comment': 'monfs managed',
        'changes': {}
    }

    cluster, conf = normalize(cluster, conf)

    # Check mon_data directory
    try:
        mon_data = _mon_data(cluster, conf, mon_id)

        if not path.exists(mon_data):
            __salt__['file.mkdir'](mon_data)
            ret['changes'][mon_data] = 'New directory'
        else:
            if not __salt__['file.directory_exists'](mon_data):
                return _error(ret, 'Path already exists and is not a directory')
    except OSError as e:
        return _error(ret, '{0}'.format(e))

    # Check monfs
    if listdir(mon_data):
        try:
            tag = '{0}/{1}'.format(mon_data, TAG_FILE_NAME)

            if __salt__['file.file_exists'](tag):
                content = _tag_file_content(cluster, mon_id, auth_type, mon_key, mon_addr)

                if _file_content_cmp(tag, content):
                    return ret

            if not __salt__['file.remove'](mon_data):
                return _error(ret, 'Cleanup monfs failure')

            ret['changes'][mon_data] = 'Cleanup'

            __salt__['file.mkdir'](mon_data)
        except (IOError, OSError) as e:
            return _error(ret, '{0}'.format(e))

    try:
        keyring = ''

        # Create temp mon keyring
        if auth_type == 'cephx' and mon_key:
            keyring = utils.mkstemp()
            data = __salt__['ceph_key.manage_keyring'](keyring,
                                                       'mon.', mon_key,
                                                       mon_caps='allow *')
            if not data['result']:
                return _error(ret, '{0}'.format(data['comment']))

        # Do the real job
        cmd = ['ceph-mon']

        cmd.append('--cluster {0}'.format(cluster))
        cmd.append('--conf {0}'.format(conf))
        cmd.append('--id {0}'.format(mon_id))
        cmd.append('--mkfs')

        if keyring:
            cmd.append('--keyring {0}'.format(keyring))
        if mon_addr:
            cmd.append('--public-addr {0}'.format(mon_addr))

        cmd = ' '.join(cmd)

        data = __salt__['cmd.run_all'](cmd)

        if data['retcode']:
            return _error(ret, '{0}'.format(data['stderr']))
        ret['changes']['monfs'] = data['stdout']
    finally:
        utils.safe_rm(keyring)

    # Create a magic file to prevent the next try
    if not _monfs_finalize(cluster, conf, mon_id, auth_type, mon_key, mon_addr):
        return _error(ret, 'Create tag file failure')

    ret['changes']['tag'] = 'New tag file'

    return ret

def remove_monfs(mon_id,
                 cluster=CEPH_CLUSTER,
                 conf=CEPH_CONF):
    ret = {
        'name': mon_id,
        'result': True,
        'comment': 'monfs removed',
        'changes': {}
    }

    cluster, conf = normalize(cluster, conf)

    mon_data = _mon_data(cluster, conf, mon_id)

    if not path.exists(mon_data):
        ret['comment'] = 'mon_data directory does not exist, skip'
        return ret

    if not __salt__['file.directory_exists'](mon_data):
        return _error(ret, 'Path exists and is not a directory')

    if __salt__['file.remove'](mon_data):
        ret['changes'][mon_data] = 'Removed'
    else:
        return _error(ret, 'Remove mon_data directory failure')

    return ret

def manage_conf(mon_id,
                mon_addr='',
                cluster=CEPH_CLUSTER,
                conf=CEPH_CONF):
    ret = {
        'name': mon_id,
        'result': True,
        'comment': 'mon.{0} section of ceph.conf managed'.format(mon_id),
        'changes': {}
    }

    cluster, conf = normalize(cluster, conf)

    section_name = 'mon.{0}'.format(mon_id)

    options = {}
    options['host'] = __grains__['host'] if __grains__['host'] else 'localhost'
    if mon_addr:
        options['mon addr'] = mon_addr

    section = {section_name: options}

    data = __salt__['ini.get_section'](conf, section_name)
    if data == section[section_name]:
        return ret

    data = __salt__['ini.set_option'](conf, section)

    # This relies on implementation of 'ini' module
    if 'error' in data:
        return _error(ret, data['error'])

    ret['changes'].update(data['changes'])

    return ret

def remove_conf(mon_id,
                cluster=CEPH_CLUSTER,
                conf=CEPH_CONF):
    ret = {
        'name': mon_id,
        'result': True,
        'comment': 'mon.{0} section of ceph.conf removed'.format(mon_id),
        'changes': {}
    }

    cluster, conf = normalize(cluster, conf)

    section_name = 'mon.{0}'.format(mon_id)

    data = __salt__['ini.get_section'](conf, section_name)
    if not data:
        ret['comment'] = 'mon.{0} section does not exist, skip'.format(mon_id)
        return ret

    data = __salt__['ini.remove_section'](conf, section_name)

    if data:
        ret['changes'][section_name] = 'Removed'

    return ret

def manage(mon_id,
           auth_type='none',
           mon_key='',
           mon_addr='',
           cluster=CEPH_CLUSTER,
           conf=CEPH_CONF):
    ret = {
        'name': mon_id,
        'result': True,
        'comment': 'mon.{0} managed'.format(mon_id),
        'changes': {}
    }

    cluster, conf = normalize(cluster, conf)

    data = manage_monfs(mon_id, auth_type, mon_key, mon_addr, cluster, conf)

    if not data['result']:
        return _error(ret, data['comment'])

    ret['changes'].update(data['changes'])

    data = manage_conf(mon_id, mon_addr, cluster, conf)

    if not data['result']:
        return _error(ret, data['comment'])

    ret['changes'].update(data['changes'])

    return ret

def remove(mon_id,
           cluster=CEPH_CLUSTER,
           conf=CEPH_CONF):
    ret = {
        'name': mon_id,
        'result': True,
        'comment': 'mon.{0} removed'.format(mon_id),
        'changes': {}
    }

    cluster, conf = normalize(cluster, conf)

    # Remove ceph.conf
    data = remove_conf(mon_id, cluster, conf)

    if not data['result']:
        return _error(ret, data['comment'])

    ret['changes'].update(data['changes'])

    # Remove monfs
    data = remove_monfs(mon_id, cluster, conf)
    if not data['result']:
        return _error(ret, data['comment'])

    ret['changes'].update(data['changes'])

    return ret

def start(mon_id='',
          cluster=CEPH_CLUSTER,
          conf=CEPH_CONF):
    cluster, conf = normalize(cluster, conf)

    cmd = ['/etc/init.d/ceph']

    cmd.append('--cluster {0}'.format(cluster))
    cmd.append('--conf {0}'.format(conf))
    cmd.append('start')
    if mon_id:
        cmd.append('mon.{0}'.format(mon_id))
    else:
        cmd.append('mon')

    cmd = ' '.join(cmd)

    return __salt__['cmd.run_all'](cmd)

def stop(mon_id='',
         cluster=CEPH_CLUSTER,
         conf=CEPH_CONF):
    cluster, conf = normalize(cluster, conf)

    cmd = ['/etc/init.d/ceph']

    cmd.append('--cluster {0}'.format(cluster))
    cmd.append('--conf {0}'.format(conf))
    cmd.append('stop')
    if mon_id:
        cmd.append('mon.{0}'.format(mon_id))
    else:
        cmd.append('mon')

    cmd = ' '.join(cmd)

    return __salt__['cmd.run_all'](cmd)

def restart(mon_id='',
            cluster=CEPH_CLUSTER,
            conf=CEPH_CONF):
    cluster, conf = normalize(cluster, conf)

    cmd = ['/etc/init.d/ceph']

    cmd.append('--cluster {0}'.format(cluster))
    cmd.append('--conf {0}'.format(conf))
    cmd.append('restart')
    if mon_id:
        cmd.append('mon.{0}'.format(mon_id))
    else:
        cmd.append('mon')

    cmd = ' '.join(cmd)

    return __salt__['cmd.run_all'](cmd)

def status(mon_id='',
           cluster=CEPH_CLUSTER,
           conf=CEPH_CONF):
    cluster, conf = normalize(cluster, conf)

    cmd = ['/etc/init.d/ceph']

    cmd.append('--cluster {0}'.format(cluster))
    cmd.append('--conf {0}'.format(conf))
    cmd.append('status')
    if mon_id:
        cmd.append('mon.{0}'.format(mon_id))
    else:
        cmd.append('mon')

    cmd = ' '.join(cmd)

    return __salt__['cmd.run_all'](cmd)
