ceph:
  bootstrap:
    ntp:
      {% if grains['os_family'] in ['Debian',] %}
      pkg: ntp
      svc: ntp
      cfile: /etc/ntp.conf
      srvs:
        - 192.168.133.10
      {% elif grains['os_family'] in ['RedHat'] %}
      pkg: ntp
      svc: ntpd
      cfile: /etc/ntp.conf
      srvs:
        - 192.168.133.10
      {% endif %}
