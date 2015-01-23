{% if grains['os_family'] in ['Debian', 'Deepin'] %}
ceph:
  ntp:
    srvs:
      - 0.ubuntu.pool.ntp.org
      - 1.ubuntu.pool.ntp.org
      - 2.ubuntu.pool.ntp.org
      - 3.ubuntu.pool.ntp.org
{% elif grains['os_family'] in ['RedHat'] %}
ceph:
  ntp:
    srvs:
      - 0.centos.pool.ntp.org
      - 1.centos.pool.ntp.org
      - 2.centos.pool.ntp.org
      - 3.centos.pool.ntp.org
{% endif %}