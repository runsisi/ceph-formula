{% from 'ceph/lookup.jinja' import ceph with context %}

{% set repos = ceph.repos | default({}, True) %}
{% set version = ceph.ceph_version %}

include:
  - ceph.repo

ceph.pkg:
  pkg.installed:
    - name: ceph
    - version: {{ version }}
    - require:
      {% for repo in repos %}
      - pkgrepo: ceph.repo.{{ repo.name }}
      {% endfor %}
