ceph:
  bootstrap:
    ntp:
      peers:
        - 10.118.202.17
        - 10.118.202.182
      {% if grains['os_family'] in ['Debian',] %}
      srvs:
        - 0.ubuntu.pool.ntp.org
        - 1.ubuntu.pool.ntp.org
        - 2.ubuntu.pool.ntp.org
        - 3.ubuntu.pool.ntp.org
      {% elif grains['os_family'] in ['RedHat'] %}
      srvs:
        - 0.centos.pool.ntp.org
        - 1.centos.pool.ntp.org
        - 2.centos.pool.ntp.org
        - 3.centos.pool.ntp.org
      {% endif %}