{% from "ceph/lookup.jinja" import base with context %}
{% from "ceph/lookup.jinja" import config with context %}

{% if base.manage_repo %}
include:
  - ceph.repo
{% endif %}

ceph.pkgs:
  pkg.installed:
    - names:
    {% for pkg in base.pkgs %}
      - {{ pkg }}
    {% endfor %}
    {% if base.manage_repo %}
    {% for repo in base.repos %}
    - require:
      - pkgrepo: {{ repo }}
    {% endfor %}
    {% endif %}

ceph.config:
  file.managed:
    - name: /etc/ceph/{{ config.cluster }}.conf
    - template: jinja
    - source: salt://ceph/files/ceph.conf
    - makedirs: True
    - user: root
    - group: root
    - mode: 644
    - require:
      - pkg: ceph.pkgs