ceph:
  ### repository for ceph and all other packages ###
  repos:
    - name: clove
      humanname: All packages for ceph and others
      baseurl: http://10.118.202.154/ZXTECS/0.87/el7/x86_64
      gpgcheck: 0

  ### NTP servers ###
  ntp_servers:
    - 192.168.233.10

  ### salt-minion parameters ###
  minion_master: 192.168.233.10
  minion_version: 2014.7.0-3.el7

  ### The version of ceph to be installed ###
  ceph_version: 0.87-0.el7.centos

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
    ### data and journal on the same disk /dev/sdb
    #- data: /dev/sdb
    ### data on /dev/sdc and journal on /dev/sde
    #- data: /dev/sdc
    #  journal: /dev/sde
    ### data on /dev/sdd and journal on /dev/sde
    #- data: /dev/sdd
    #  journal: /dev/sde
