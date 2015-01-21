ceph.mon.setup:
  salt.state:
    - tgt: 'brs17,brs182'
    - tgt_type: list
    - sls:
      - ceph.deploy.mon

ceph.osd.setup:
  salt.state:
    - tgt: 'brs17,brs182'
    - tgt_type: list
    - sls:
      - ceph.deploy.osd
    - require:
      - salt: ceph.mon.setup

ceph.client.setup:
  salt.state:
    - tgt: 'brs17'
    - tgt_type: list
    - sls:
      - ceph.deploy.client
    - require:
      - salt: ceph.osd.setup