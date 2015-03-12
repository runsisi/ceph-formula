ceph:
  bootstrap:
    salt:
      minion:
        master_resolv: 1
        master_ip: 10.118.202.17
        pkgs:
          {% if grains['os_family'] in ['Debian',] %}
          salt-minion: 2014.7.1+ds-1{{ grains['oscodename'] }}1
          {% elif grains['os_family'] in ['RedHat'] %}
          salt-minion: 2014.7.0-3.el{{ grains['osmajorrelease'] }}
          {% endif %}