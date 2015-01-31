{% if grains['os_family'] in ['Debian',] %}
ceph:
  pkg:
    pkgs:
      ceph: 0.87-1{{ grains['oscodename'] }}
    manage_repo: 1
{% elif grains['os_family'] in ['RedHat'] %}
{% if grains['osmajorrelease'] == '6' %}
ceph:
  pkg:
    pkgs:
      ceph: 0.87-0.el6
{% elif grains['osmajorrelease'] == '7' %}
ceph:
  pkg:
    pkgs:
      ceph: 0.87-0.el7.centos
{% endif %}
{% endif %}