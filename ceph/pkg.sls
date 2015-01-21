{% from 'ceph/lookup.jinja' import base with context %}

{% if base.manage_repo %}
include:
  - ceph.repo
{% endif %}

{% for pkg, ver in base.pkgs.iteritems() %}
ceph.pkg.{{ pkg }}.{{ ver }}.install:
  pkg.installed:
    - name: {{ pkg }}
    - version: {{ ver }}
    {% if base.manage_repo %}
    - require:
      {% for repo in base.repos %}
      - pkgrepo: ceph.repo.{{ repo.humanname }}.setup
      {% endfor %}
    {% endif %}
{% endfor %}

