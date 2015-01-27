{% from 'ceph/bootstrap/lookup.jinja' import bootstrap with context %}

{% set master_resolv = bootstrap.salt.minion.master_resolv %}
{% set master_ip = bootstrap.salt.minion.master_ip %}
{% set pkgs = bootstrap.salt.minion.pkgs | default({}) %}
{% set repos = bootstrap.repo.repos | default({}) %}

include:
  - ceph.bootstrap.repo

{% if master_resolv %}
ceph.bootstrap.salt.master.resolv:
  host.present:
    - name: salt
    - ip: {{ master_ip }}
    - watch_in:
      - service: ceph.bootstrap.salt.minion.start
{% endif %}

{% for pkg, ver in pkgs.iteritems() %}
ceph.bootstrap.minion.pkg.{{ pkg }}.{{ ver }}.install:
  pkg.installed:
    - name: {{ pkg }}
    - version: {{ ver }}
    - require:
      {% if master_resolv %}
      - host: ceph.bootstrap.salt.master.resolv
      {% endif %}
      {% for repo in repos %}
      - pkgrepo: ceph.bootstrap.repo.{{ repo.humanname }}.setup
      {% endfor %}
{% endfor %}

ceph.bootstrap.salt.minion.start:
  service.running:
    - name: salt-minion
    - enable: True
    - require:
      {% for pkg, ver in pkgs.iteritems() %}
      - pkg: ceph.bootstrap.minion.pkg.{{ pkg }}.{{ ver }}.install
      {% endfor %}