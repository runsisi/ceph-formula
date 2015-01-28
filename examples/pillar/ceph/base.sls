{% if salt['grains.get']('os_family') in ['Debian',] %}
ceph:
  repo:
    manage_repo: 1
    repos:
      - name: deb http://ceph.com/debian-giant {{ salt['grains.get']('oscodename') }} main
        humanname: ceph
        dist: {{ salt['grains.get']('oscodename') }}
        file: /etc/apt/sources.list.d/ceph.list
        key_url: https://ceph.com/git/?p=ceph.git;a=blob_plain;f=keys/release.asc
  pkg:
    pkgs:
      ceph: 0.87-1{{ grains['oscodename'] }}
    manage_repo: 1
{% elif salt['grains.get']('os_family') in ['RedHat'] %}
ceph:
  repo:
    manage_repo: 1
    repos:
      - name: ceph
        humanname: ceph
        baseurl: http://ceph.com/rpm-giant/el{{ grains['osmajorrelease'] }}/$basearch
        gpgcheck: 1
        gpgkey: https://ceph.com/git/?p=ceph.git;a=blob_plain;f=keys/release.asc
  pkg:
    pkgs:
      {% if grains['osmajorrelease'] == '6' %}
      ceph: 0.87-0.el6
      {% elif grains['osmajorrelease'] == '7' %}
      ceph: 0.87-0.el7.centos
      {% endif %}
{% endif %}