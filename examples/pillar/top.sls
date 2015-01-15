base:
  '*':
    - ceph.pkg
    - ceph.conf
  'brs17, ceph10':
    - match: list
    - ceph.mon
    - ceph.osd