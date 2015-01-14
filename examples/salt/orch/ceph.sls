ceph.mon.setup:
  salt.state:
    - tgt: 'brs82, brs98, brs159'
    - tgt_type: list
    - sls:
      - ceph.mon

ceph.osd.setup:
  salt.state:
    - tgt: 'brs8'
    - tgt_type: list
    - sls:
      - ceph.osd

ceph.client.setup:
  salt.state:
    - tgt: 'brs8'
    - tgt_type: list
    - sls:
      - ceph.client