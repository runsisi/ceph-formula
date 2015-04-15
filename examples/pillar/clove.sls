ceph:
  ### repository for ceph and all other packages ###
  repo: http://host/to/repo/clove/ceph/0.87/el7/x86_64/

  ### FQDN or IP address of salt-master host ###
  minion_master: 192.168.233.10

  ### NTP servers ###
  ntp_servers:
    - 192.168.233.10

  ### ceph cluster keys ###
  mon_key: AQAAA8FU2AnFEhAA/5cDGZk5PjFjUMy8q7+Csw==
  admin_key: AQAOA8FU0GaGKRAA6BW1dc/zwTcah70r6Ow1mg==
  bootstrap_osd_key: AQAcA8FU8LWzHhAAN7+cwxF7KJuf5vSo52fPsQ==
  bootstrap_mds_key: AQAmA8FUgETmGBAAO6AX1NUUemA7heYnvFlQ9w==

  ### ceph cluster parameters ###
  ceph_config:
    global:
      #fsid: cbc99ef9-fbc3-41ad-a726-47359f8d84b3
      #mon_initial_members: ceph1
      #mon_host: 192.168.233.11,192.168.233.12,192.168.233.13,
      #public_network: 192.168.233.0/24
      #cluster_network: 192.168.234.0/24

  ### ceph OSD(s) to be created ###
  osds:
    #/dev/sdb: /dev/sdb    # data and journal on the same disk /dev/sdb
    #/dev/sdc:             # data and journal on the same disk /dev/sdc
    #/dev/sdd: /dev/sdf    # data on /dev/sdd and journal on /dev/sdf
    #/dev/sde: /dev/sdf    # data on /dev/sde and journal on /dev/sdf
