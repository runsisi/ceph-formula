ceph:
  bootstrap:
    ntp:
      pkg: ntp
      svc: ntpd
      cfile: /etc/ntp.conf
      srvs:
        - 192.168.133.10