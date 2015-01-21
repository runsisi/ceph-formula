{% from 'ceph/deploy/lookup.jinja' import ceph with context %}

{% set manage_repo = ceph.base.manage_repo | default(0) %}
{% set pkgs = ceph.base.pkgs | default({}) %}

{% if manage_repo %}
include:
  - ceph.deploy.repo
{% endif %}

{% for pkg, ver in pkgs.iteritems() %}

ceph.pkg.{{ pkg }}.{{ ver }}.install:
  pkg.installed:
    - name: {{ pkg }}
    - version: {{ ver }}
    {% if ceph.base.manage_repo %}
    - require:
      {% for repo in ceph.base.repos %}
      - pkgrepo: ceph.repo.{{ repo.humanname }}.setup
      {% endfor %}
    {% endif %}

{% endfor %}

