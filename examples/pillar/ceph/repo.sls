{% if grains['os_family'] in ['Debian',] %}
ceph:
  repo:
    manage_repo: 1
    repos:
      - name: deb http://ceph.com/debian-giant {{ grains['oscodename'] }} main
        humanname: ceph
        dist: {{ grains['oscodename'] }}
        file: /etc/apt/sources.list.d/ceph.list
        key_url: https://ceph.com/git/?p=ceph.git;a=blob_plain;f=keys/release.asc
{% elif grains['os_family'] in ['RedHat'] %}
ceph:
  repo:
    manage_repo: 1
    repos:
      - name: ceph
        humanname: ceph
        baseurl: http://ceph.com/rpm-giant/el{{ grains['osmajorrelease'] }}/$basearch
        gpgcheck: 1
        gpgkey: https://ceph.com/git/?p=ceph.git;a=blob_plain;f=keys/release.asc
{% endif %}