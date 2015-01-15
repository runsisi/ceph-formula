ceph.mon.setup:
  salt.state:
    - tgt: 'brs17, ceph46'
    - tgt_type: list
    - sls:
      - ceph.mon

ceph.osd.setup:
  salt.state:
    - tgt: 'brs17, ceph46'
    - tgt_type: list
    - sls:
      - ceph.osd
    - require:
      - salt: ceph.mon.setup

ceph.client.setup:
  salt.state:
    - tgt: 'brs17'
    - tgt_type: list
    - sls:
      - ceph.client
    - require:
      - salt: ceph.osd.setup