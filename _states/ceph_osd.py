# -*- coding: utf-8 -*-
'''
Manage ceph OSDs.

author: runsisi AT hust.edu.cn
'''

__virtualname__ = 'ceph_osd'

CEPH_CLUSTER = 'ceph'                   # Default cluster name


def __virtual__():
    '''
    Only load if the ceph_deploy module is available
    '''
    return __virtualname__ if 'ceph_deploy.osd_manage' in __salt__ else False


def _error(ret, msg):
    ret['result'] = False
    ret['comment'] = msg
    return ret


def present(name,
            journal='',
            cluster=CEPH_CLUSTER):
    return __salt__['ceph_deploy.osd_manage'](name, journal, cluster)


def absent(name,
           journal='',
           cluster=CEPH_CLUSTER):
    return __salt__['ceph_deploy.osd_unmanage'](name, journal, cluster)
