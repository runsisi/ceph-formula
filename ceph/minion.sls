{% from 'ceph/lookup.jinja' import ceph with context %}

{% set master = ceph.minion_master %}

{% set clove = {
    'master': master,
    'id': grains['id'],
} %}

include:
  - ceph.repo

ceph.minion.pkg:
  pkg.latest:
    - name: salt-minion
    - fromrepo: clove
    - refresh: True
    - require:
      - pkgrepo: ceph.repo

ceph.minion.conf:
  file.managed:
    - name: /etc/salt/minion.d/clove.conf
    - makedirs: True
    - source: salt://ceph/files/clove.conf
    - template: jinja
    - context:
        clove: {{ clove }}
    - require:
      - pkg: ceph.minion.pkg

ceph.minion.daemon:
  service.running:
    - name: salt-minion
    - enable: True
    - watch:
      - pkg: ceph.minion.pkg
      - file: ceph.minion.conf
