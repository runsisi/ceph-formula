{% from 'ceph/deploy/lookup.jinja' import ceph with context %}

{% set pkgs = ceph.base.pkgs | default({}) %}
{% set cluster = ceph.conf.cluster | default('') | trim | default('ceph', True) %}
{% set auth_type = ceph.conf.global.auth_type | default('') | trim | default('cephx', True) %}
{% set auth_type = 'cephx' if auth_type != 'none' else 'none' %}
{% set global_conf = ceph.conf.global | default({}) %}
{% set mon_conf = ceph.conf.mon | default({}) %}
{% set osd_conf = ceph.conf.osd | default({}) %}

{% do global_conf.pop('auth_type') %}

{% if auth_type == 'cephx' %}
{% do global_conf.update({
    'auth_cluster_required': 'cephx',
    'auth_service_required': 'cephx',
    'auth_client_required': 'cephx' }) %}
{% else %}
{% do global_conf.update({
    'auth_cluster_required': 'none',
    'auth_service_required': 'none',
    'auth_client_required': 'none' }) %}
{% endif %}

include:
  - ceph.deploy.pkg

ceph.conf.setup:
  file.managed:
    - name: /etc/ceph/{{ cluster }}.conf
    - makedirs: True
    - user: root
    - group: root
    - mode: 644
    - require:
      {% for pkg, ver in pkgs.iteritems() %}
      - pkg: ceph.pkg.{{ pkg }}.{{ ver }}.install
      {% endfor %}
  ini.sections_present:
    - name: /etc/ceph/{{ cluster }}.conf
    - sections:
        {% if global_conf %}
        global:
          {% for key, value in global_conf.iteritems() %}
          {{ key }}: '{{ value }}'
          {% endfor %}
        {% endif %}
        {% if mon_conf %}
        mon:
          {% for key, value in mon_conf.iteritems() %}
          {{ key }}: '{{ value }}'
          {% endfor %}
        {% endif %}
        {% if osd_conf %}
        osd:
          {% for key, value in osd_conf.iteritems() %}
          {{ key }}: '{{ value }}'
          {% endfor %}
        {% endif %}
    - require:
      - file: ceph.conf.setup

ceph.conf.cleanup:
  ini.sections_absent:
    - name: /etc/ceph/{{ cluster }}.conf
    - sections:
      - {{ 'global' if not global_conf else '' }}
      - {{ 'mon' if not mon_conf else '' }}
      - {{ 'osd' if not osd_conf else '' }}
    - require:
      - ini: ceph.conf.setup
