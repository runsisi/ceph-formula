{% from 'ceph/lookup.jinja' import ceph with context %}

{% set repo = ceph.repository %}

ceph.repo:
  pkgrepo.managed:
    - name: clove
    - humanname: Packages for ceph and others
    - baseurl: {{ repo }}
    - gpgcheck: 0
