{% from "ceph/lookup.jinja" import conf with context %}

include:
  - ceph.pkg

ceph.conf.setup:
  file.managed:
    - name: /etc/ceph/{{ conf.cluster }}.conf
    - template: jinja
    - source: salt://ceph/files/ceph.conf
    - makedirs: True
    - user: root
    - group: root
    - mode: 644
    - require:
      - pkg: ceph.pkg.install