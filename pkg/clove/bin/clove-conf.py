#!/usr/bin/env python
# -*- coding: utf-8 -*-
# runsisi AT hust.edu.cn

#ceph:
#  # cluster keys
#  mon_key: AQAAA8FU2AnFEhAA/5cDGZk5PjFjUMy8q7+Csw==
#  admin_key: AQAOA8FU0GaGKRAA6BW1dc/zwTcah70r6Ow1mg==
#  bootstrap_osd_key: AQAcA8FU8LWzHhAAN7+cwxF7KJuf5vSo52fPsQ==
#  bootstrap_mds_key: AQAmA8FUgETmGBAAO6AX1NUUemA7heYnvFlQ9w==
#
#  # ceph packages to be installed
#  pkg:
#    pkgs:
#      ceph: 0.87-0.el7.centos
#
#  # ceph yum repository
#  repo:
#    manage_repo: 1
#    repos:
#      - name: ceph
#        humanname: ceph
#        baseurl: http://10.118.202.154/rpm-giant/el7/$basearch
#        gpgcheck: 0
#
#  # cluster parameters
#  conf:
#    global:
#      fsid: cbc99ef9-fbc3-41ad-a726-47359f8d84b3
#      mon_initial_members: ceph-osd1.test,
#      mon_host: 192.168.133.10:6789,192.168.133.11:6789,192.168.133.12:6789,
#      public_network: 192.168.133.0/24
#      cluster_network: 192.168.134.0/24
#
#  # OSD(s) to be created
#  osd:
#    osds:
#      - data: /dev/sdb
#        journal: /dev/sdf
#      - data: /dev/sdc
#        journal: /dev/sdf
#      - data: /dev/sdd
#        journal: /dev/sdf
#      - data: /dev/sde
#        journal: /dev/sdf

