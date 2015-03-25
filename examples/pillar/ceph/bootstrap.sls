ceph:
  bootstrap:
    # salt parameters
    salt:
      minion:
        master_ip: 10.118.202.17
        pkgs:
          salt-minion: 2014.7.0-3.el7

    # NTP parameters
    ntp:
      pkg: ntp
      svc: ntpd
      cfile: /etc/ntp.conf
      srvs:
        - 192.168.133.10

    # system basic yum repositories
    repo:
      cleanup: 1
      repos:
        - name: base
          humanname: base
          baseurl: http://10.118.202.154/centos/7/os/$basearch
          gpgcheck: 1
          gpgkey: http://10.118.202.154/centos/RPM-GPG-KEY-CentOS-7

        - name: extras
          humanname: extras
          baseurl: http://10.118.202.154/centos/7/extras/$basearch
          gpgcheck: 1
          gpgkey: http://10.118.202.154/centos/RPM-GPG-KEY-CentOS-7

        - name: updates
          humanname: updates
          baseurl: http://10.118.202.154/centos/7/updates/$basearch
          gpgcheck: 1
          gpgkey: http://10.118.202.154/centos/RPM-GPG-KEY-CentOS-7

        - name: epel
          humanname: epel
          baseurl: http://10.118.202.154/epel/7/$basearch
          gpgcheck: 1
          gpgkey: http://10.118.202.154/epel/RPM-GPG-KEY-EPEL-7
