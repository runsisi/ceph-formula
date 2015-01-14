base:
  '*':
    - ceph.pkg
    - ceph.conf
  'brs8, brs98, brs159':
    - match: list
    - ceph.mon
    - ceph.osd