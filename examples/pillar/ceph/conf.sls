ceph:
  mon_key: AQAAA8FU2AnFEhAA/5cDGZk5PjFjUMy8q7+Csw==
  admin_key: AQAOA8FU0GaGKRAA6BW1dc/zwTcah70r6Ow1mg==
  bootstrap_osd_key: AQAcA8FU8LWzHhAAN7+cwxF7KJuf5vSo52fPsQ==
  bootstrap_mds_key: AQAmA8FUgETmGBAAO6AX1NUUemA7heYnvFlQ9w==

  conf:
    global:
      fsid: cbc99ef9-fbc3-41ad-a726-47359f8d84b3
      mon_initial_members: ceph-osd1.test,
      mon_host: 192.168.133.10:6789,192.168.133.11:6789,192.168.133.12:6789,
      public_network: 192.168.133.0/24
      cluster_network: 192.168.134.0/24