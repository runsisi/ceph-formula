# -*- coding: utf-8 -*-
'''
Manage ceph key.

author: runsisi AT hust.edu.cn
'''

__virtualname__ = 'ceph_key'

CEPH_CLUSTER = 'ceph'                   # Default cluster name


def __virtual__():
    '''
    Only load if the ceph_deploy module is available
    '''
    return __virtualname__ if 'ceph_deploy.keyring_manage' in __salt__ else False


def keyring_present(name,
                    entity_name,
                    entity_key,
                    mon_caps='',
                    osd_caps='',
                    mds_caps='',
                    user='root',
                    group='root',
                    mode='600'):
    return __salt__['ceph_deploy.keyring_manage'](name,
                                                  entity_name, entity_key,
                                                  mon_caps, osd_caps, mds_caps,
                                                  user, group, mode)


def keyring_absent(name,
                   entity_name=''):
    return __salt__['ceph_deploy.keyring_unmanage'](name, entity_name)


def auth_present(name,
                 entity_key,
                 admin_name,
                 admin_key,
                 mon_caps=None,
                 osd_caps=None,
                 mds_caps=None,
                 cluster=CEPH_CLUSTER):
    return __salt__['ceph_deploy.auth_manage'](name, entity_key,
                                               admin_name, admin_key,
                                               mon_caps, osd_caps, mds_caps,
                                               cluster)


def auth_absent(name,
                admin_name,
                admin_key,
                cluster=CEPH_CLUSTER):
    return __salt__['ceph_deploy.auth_unmanage'](name,
                                                 admin_name, admin_key,
                                                 cluster)
