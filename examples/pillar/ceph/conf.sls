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
      osd_pool_default_size: 2
      osd_pool_default_min_size: 1
      osd_crush_chooseleaf_type: 0
      mon_initial_members: {{ grains['host'] }},
    mon: {}
    osd: {}
    mons:
      - id: {{ grains['host'] }}
        addr: {{ grains['ipv4'][0] + ':6789' }}