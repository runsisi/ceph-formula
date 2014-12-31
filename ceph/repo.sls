{% from "ceph/lookup.jinja" import ceph with context %}

{% if ceph.manage_repo %}
{% if grains['os_family'] == 'Debian' or grains['os_family'] == 'Deepin' %}
ceph-repo:
  pkgrepo.managed:
    - name: deb http://ceph.com/debian-{{ ceph.release }} {{ grains['oscodename'] }} main
    - dist: {{ grains['oscodename'] }}
    - file: /etc/apt/sources.list.d/ceph.list
    - key_url: https://ceph.com/git/?p=ceph.git;a=blob_plain;f=keys/release.asc
{% elif grains['os_family'] == 'RedHat' %}
ceph-repo:
  pkgrepo.managed:
    - name: ceph
    - humanname: ceph
    - baseurl: http://ceph.com/rpm-{{ ceph.release }}/el{{ grains['osmajorrelease'][0] }}/$basearch
    - gpgcheck: 1
    - gpgkey: https://ceph.com/git/?p=ceph.git;a=blob_plain;f=keys/release.asc
ceph-noarch-repo:
  pkgrepo.managed:
    - name: ceph-noarch
    - humanname: ceph-noarch
    - baseurl: http://ceph.com/rpm-{{ ceph.release }}/el{{ grains['osmajorrelease'][0] }}/noarch
    - gpgcheck: 1
    - gpgkey: https://ceph.com/git/?p=ceph.git;a=blob_plain;f=keys/release.asc
{% endif %}
{% endif %}