ceph:
  cluster: ceph
  auth_type: cephx
  mon_key: AQAAA8FU2AnFEhAA/5cDGZk5PjFjUMy8q7+Csw==
  admin_key: AQAOA8FU0GaGKRAA6BW1dc/zwTcah70r6Ow1mg==
  bootstrap_osd_key: AQAcA8FU8LWzHhAAN7+cwxF7KJuf5vSo52fPsQ==
  bootstrap_mds_key: AQAmA8FUgETmGBAAO6AX1NUUemA7heYnvFlQ9w==

  conf:
    global:
      fsid: cbc99ef9-fbc3-41ad-a726-47359f8d84b3
      public_network: 10.118.202.0/24
      cluster_network: 10.118.202.0/24
      mon_initial_members: brs17,
    mon: {}
    osd:
      osd_pool_default_size: 2
      osd_pool_default_min_size: 1
      osd_crush_chooseleaf_type: 0
    mons:
      - id: brs17
        addr: 10.118.202.17
      - id: brs182
        host: brs182
        addr: 10.118.202.182