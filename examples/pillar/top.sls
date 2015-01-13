base:
  '*':
    - ceph.pkg
    - ceph.conf
  'brs159, brs98, brs82':
    - match: list
    - ceph.mon
  'brs8':
    - match: list
    - ceph.osd
  'runsisi-pc':
    - match: list
    - ceph.mon
    - ceph.osd