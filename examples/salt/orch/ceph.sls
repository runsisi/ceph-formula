ceph.mon.setup:
  salt.state:
    - tgt: 'brs17, ceph10'
    - tgt_type: list
    - sls:
      - ceph.mon

ceph.osd.setup:
  salt.state:
    - tgt: 'brs17, ceph10'
    - tgt_type: list
    - sls:
      - ceph.osd

ceph.client.setup:
  salt.state:
    - tgt: 'brs17'
    - tgt_type: list
    - sls:
      - ceph.client