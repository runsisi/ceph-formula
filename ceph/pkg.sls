{% from 'ceph/lookup.jinja' import ceph with context %}

{% set manage_repo = ceph.repo.manage_repo | default(0, True) %}
{% set repos = ceph.repo.repos | default({}, True) %}
{% set pkgs = ceph.pkg.pkgs | default({}, True) %}

{% if manage_repo %}
include:
  - ceph.repo
{% endif %}

{% for pkg, ver in pkgs.iteritems() %}

ceph.pkg.{{ pkg }}.{{ ver }}.install:
  pkg.installed:
    - name: {{ pkg }}
    - version: {{ ver }}
    {% if manage_repo %}
    - require:
      {% for repo in repos %}
      - pkgrepo: ceph.repo.{{ repo.humanname }}.setup
      {% endfor %}
    {% endif %}

{% endfor %}

