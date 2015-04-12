ceph:
  bootstrap:

    ### salt parameters ###

    salt:
      minion:
        master: 10.118.202.17
        pkgs:
          salt-minion: 2014.7.0-3.el7


    ### NTP parameters ###

    ntp:
      pkg: ntp
      svc: ntpd
      cfile: /etc/ntp.conf
      srvs:
        - 192.168.133.10


    ### repositories for ceph dependencies ###

    repo:
      cleanup: 1
      repos:
        - name: ceph-dep
          humanname: ceph-dep
          baseurl: http://10.118.202.154/ceph/ceph-dep/0.87/el7/$basearch
          gpgcheck: 0
