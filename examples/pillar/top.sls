base:
  '*':
    - ceph.pkg
    - ceph.conf
  'brs17,brs182':
    - match: list
    - ceph.mon
    - ceph.osd