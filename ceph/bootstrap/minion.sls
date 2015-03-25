{% from 'ceph/bootstrap/lookup.jinja' import bootstrap with context %}

{% set master_ip = bootstrap.salt.minion.master_ip %}
{% set pkgs = bootstrap.salt.minion.pkgs | default({}) %}
{% set repos = bootstrap.repo.repos | default({}) %}

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
    - contents: 'master: {{ master_ip }}'

ceph.bootstrap.salt.minion.start:
  service.running:
    - name: salt-minion
    - enable: True
    - watch:
      - file: ceph.bootstrap.minion.setup
