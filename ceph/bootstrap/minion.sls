{% from 'ceph/bootstrap/lookup.jinja' import bootstrap with context %}

{% set master = bootstrap.salt.minion.master %}
{% set pkgs = bootstrap.salt.minion.pkgs | default({}) %}
{% set repos = bootstrap.repo.repos | default({}) %}

{% set clove = {
    'master': master,
    'id': grains['id'],
} %}

include:
  - ceph.bootstrap.repo

{% for pkg, ver in pkgs.iteritems() %}
ceph.bootstrap.minion.pkg.{{ pkg }}.{{ ver }}.install:
  pkg.installed:
    - name: {{ pkg }}
    - version: {{ ver }}
    - require_in:
      - file: ceph.bootstrap.minion.setup
    - require:
      {% for repo in repos %}
      - pkgrepo: ceph.bootstrap.repo.{{ repo.humanname }}.setup
      {% endfor %}
{% endfor %}

ceph.bootstrap.minion.setup:
  file.managed:
    - name: /etc/salt/minion.d/clove.conf
    - makedirs: True
    - source: salt://ceph/bootstrap/files/clove.conf
    - template: jinja
    - context:
        clove: {{ clove }}

ceph.bootstrap.salt.minion.start:
  service.running:
    - name: salt-minion
    - enable: True
    - watch:
      - file: ceph.bootstrap.minion.setup
