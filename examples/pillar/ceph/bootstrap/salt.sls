ceph:
  bootstrap:
    salt:
      minion:
        master_resolv: 1
        master_ip: 10.118.4.36
        pkgs:
          {% if salt['grains.get']('os_family') in ['Debian',] %}
          salt-minion: 2014.7.0+ds-2{{ grains['oscodename'] }}1
          {% elif salt['grains.get']('os_family') in ['RedHat'] %}
          salt-minion: 2014.7.0-3.el{{ grains['osmajorrelease'] }}
          {% endif %}