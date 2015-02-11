# -*- coding: utf-8 -*-
'''
Manage ceph keys.

author: runsisi@hust.edu.cn
'''

__virtualname__ = 'ceph_key'

CEPH_CLUSTER = 'ceph'                   # Default cluster name
CEPH_CONF = '/etc/ceph/ceph.conf'       # Default cluster conf file

def __virtual__():
    '''
    Only load if the ceph_key module is available
    '''
    return __virtualname__ if 'ceph_key.manage_keyring' in __salt__ else False

def keyring_present(name,
                    entity_name,
                    entity_key,
                    mon_caps=None,
                    osd_caps=None,
                    mds_caps=None,
                    user='root',
                    group='root',
                    mode='600'):
    return __salt__['ceph_key.manage_keyring'](name,
                                               entity_name, entity_key,
                                               mon_caps, osd_caps, mds_caps,
                                               user, group, mode)

def keyring_absent(name,
                   entity_name=''):
    return __salt__['ceph_key.remove_keyring'](name, entity_name)

def entity_present(name,
                   entity_key,
                   admin_name,
                   admin_key,
                   mon_caps=None,
                   osd_caps=None,
                   mds_caps=None,
                   cluster=CEPH_CLUSTER,
                   conf=CEPH_CONF):
    return __salt__['ceph_key.manage_entity'](name, entity_key,
                                              admin_name, admin_key,
                                              mon_caps, osd_caps, mds_caps,
                                              cluster, conf)

def entity_absent(name,
                  admin_name,
                  admin_key,
                  cluster=CEPH_CLUSTER,
                  conf=CEPH_CONF):
    return __salt__['ceph_key.remove_entity'](name,
                                              admin_name, admin_key,
                                              cluster, conf)
