base:
  '*':
    - ceph.pkg
    - ceph.conf
  'brs82, brs98, brs159':
    - match: list
    - ceph.mon
  'brs8':
    - match: list
    - ceph.osd