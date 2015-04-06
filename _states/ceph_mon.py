# -*- coding: utf-8 -*-
'''
Manage ceph MONs.

author: runsisi AT hust.edu.cn
'''

__virtualname__ = 'ceph_mon'

CEPH_CLUSTER = 'ceph'                   # Default cluster name

def __virtual__():
    '''
    Only load if the ceph_deploy module is available
    '''
    return __virtualname__ if 'ceph_deploy.mon_manage' in __salt__ else False


def _error(ret, msg):
    ret['result'] = False
    ret['comment'] = msg
    return ret


def present(name,
            auth_type='none',
            mon_key='',
            mon_addr='',
            cluster=CEPH_CLUSTER):
    return __salt__['ceph_deploy.mon_manage'](name, auth_type, mon_key,
                                              mon_addr, cluster)


def absent(name,
           auth_type='none',
           mon_key='',
           mon_addr='',
           cluster=CEPH_CLUSTER):
    return __salt__['ceph_deploy.mon_unmanage'](name, auth_type, mon_key,
                                                mon_addr, cluster)


def running(name,
            cluster=CEPH_CLUSTER):
    ret = {
        'name': name,
        'result': True,
        'comment': 'MON: mon.{0} is running'.format(name),
        'changes': {}
    }

    if __salt__['ceph_deploy.mon_running'](name, cluster):
        return ret

    __salt__['ceph_deploy.mon_start'](name, cluster)

    ret['changes'][name] = 'Start daemon'

    return ret


def dead(name,
         cluster=CEPH_CLUSTER):
    ret = {
        'name': name,
        'result': True,
        'comment': 'MON: mon.{0} is dead'.format(name),
        'changes': {}
    }

    if not __salt__['ceph_deploy.mon_running'](name, cluster):
        return ret

    __salt__['ceph_deploy.mon_stop'](name, cluster)

    ret['changes'][name] = 'Stop daemon'

    return ret


def mod_watch(name,
              sfun=None,
              **kwargs):
    ret = {
        'name': name,
        'result': True,
        'comment': 'MON: mon.{0} restarted'.format(name),
        'changes': {}
    }

    if sfun != 'running':
        return _error(ret, 'watch requisite is not '
                           'implemented for {0}'.format(sfun))

    cluster = kwargs['cluster']

    __salt__['ceph_deploy.mon_restart'](name, cluster)

    ret['changes'][name] = 'Restart daemon'

    return ret
