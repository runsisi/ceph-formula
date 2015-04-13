ceph.mon.setup:
  salt.state:
    - tgt: 'ceph1,ceph2,ceph3'
    - tgt_type: list
    - sls:
      - ceph.mon

ceph.osd.setup:
  salt.state:
    - tgt: 'ceph1,ceph2,ceph3'
    - tgt_type: list
    - sls:
      - ceph.osd
    - require:
      - salt: ceph.mon.setup

ceph.client.setup:
  salt.state:
    - tgt: 'ceph0'
    - tgt_type: list
    - sls:
      - ceph.client
    - require:
      - salt: ceph.osd.setup
