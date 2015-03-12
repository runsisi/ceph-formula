# -*- coding: utf-8 -*-
'''
Manage ceph conf.

author: runsisi AT hust.edu.cn
'''

__virtualname__ = 'ceph_conf'

CEPH_CLUSTER = 'ceph'                   # Default cluster name


def __virtual__():
    '''
    Only load if the ceph_deploy module is available
    '''
    return __virtualname__ if 'ceph_deploy.conf_manage' in __salt__ else False


def present(ctx, cluster=CEPH_CLUSTER):
    return __salt__['ceph_deploy.conf_manage'](ctx, cluster)
