# -*- coding: utf-8 -*-
'''
Manage ceph MONs.

author: runsisi@hust.edu.cn
'''

__virtualname__ = 'ceph_mon'

CEPH_CLUSTER = 'ceph'                   # Default cluster name
CEPH_CONF = '/etc/ceph/ceph.conf'       # Default cluster conf file

def __virtual__():
    '''
    Only load if the ceph_mon module is available
    '''
    return __virtualname__ if 'ceph_mon.manage' in __salt__ else False

def _error(ret, msg):
    ret['result'] = False
    ret['comment'] = msg
    return ret

def present(name,
            auth_type='none',
            mon_key='',
            mon_addr='',
            cluster=CEPH_CLUSTER,
            conf=CEPH_CONF):
    return __salt__['ceph_mon.manage'](name, auth_type, mon_key,
                                       mon_addr, cluster, conf)

def absent(name,
           cluster=CEPH_CLUSTER,
           conf=CEPH_CONF):
    return __salt__['ceph_mon.remove'](name, cluster, conf)

def running(name,
            cluster=CEPH_CLUSTER,
            conf=CEPH_CONF):
    ret = {
        'name': name,
        'result': True,
        'comment': 'mon.{0} is running'.format(name),
        'changes': {}
    }

    cluster, conf = __salt__['ceph_mon.normalize'](cluster, conf)

    data = __salt__['ceph_mon.status'](name, cluster, conf)

    if not data['retcode']:
        return ret

    data = __salt__['ceph_mon.start'](name, cluster, conf)

    if data['retcode']:
        return _error(ret, data['stderr'])

    ret['changes'][name] = data['stdout']

    return ret

def dead(name,
         cluster=CEPH_CLUSTER,
         conf=CEPH_CONF):
    ret = {
        'name': name,
        'result': True,
        'comment': 'mon.{0} is dead'.format(name),
        'changes': {}
    }

    cluster, conf = __salt__['ceph_mon.normalize'](cluster, conf)

    data = __salt__['ceph_mon.status'](name, cluster, conf)

    if data['retcode']:
        return ret

    data = __salt__['ceph_mon.stop'](name, cluster, conf)

    if data['retcode']:
        return _error(ret, data['stderr'])

    ret['changes'][name] = data['stdout']

    return ret

def mod_watch(name,
              sfun=None,
              **kwargs):
    ret = {
        'name': name,
        'result': True,
        'comment': 'mon.{0} restarted'.format(name),
        'changes': {}
    }

    if sfun != 'running':
        return _error(ret, 'watch requisite is not '
                           'implemented for {0}'.format(sfun))

    cluster = kwargs['cluster']
    conf = kwargs['conf']

    data = __salt__['ceph_mon.restart'](name, cluster, conf)

    if data['retcode']:
        return _error(ret, data['stderr'])

    ret['changes'][name] = data['stdout']

    return ret
