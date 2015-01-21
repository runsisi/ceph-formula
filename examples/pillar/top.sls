base:
  '*':
    - ceph.deploy.base
    - ceph.deploy.conf
  'brs17,brs182':
    - match: list
    - ceph.deploy.mon
    - ceph.deploy.osd