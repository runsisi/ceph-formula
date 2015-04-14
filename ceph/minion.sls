{% from 'ceph/lookup.jinja' import ceph with context %}

{% set master = ceph.minion_master %}
{% set version = ceph.minion_version %}
{% set repos = ceph.repos | default({}, True) %}

{% set clove = {
    'master': master,
    'id': grains['id'],
} %}

include:
  - ceph.repo

ceph.minion.pkg:
  pkg.installed:
    - name: salt-minion
    - version: {{ version }}
    - require:
      {% for repo in repos %}
      - pkgrepo: ceph.repo.{{ repo.name }}
      {% endfor %}

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
      - file: ceph.minion.conf
