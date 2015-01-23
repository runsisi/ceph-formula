base:
  '*':
    - ceph.base
    - ceph.conf
    - ceph.osd
    - ceph.ntpc
  'brs17,brs182':
    - match: list
    - ceph.ntpd