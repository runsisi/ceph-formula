base:
  '*':
    - ceph.pkg
    - ceph.conf
  'brs17,ceph46':
    - match: list
    - ceph.mon
    - ceph.osd