{% from 'ceph/lookup.jinja' import ceph with context %}

{% set pkgs = ceph.pkg.pkgs | default({}) %}
{% set cluster = ceph.cluster | default('') | trim | default('ceph', True) %}
{% set auth_type = ceph.auth_type | default('') | trim | default('cephx', True) %}
{% if auth_type == 'none' %}
{% do ceph.conf.global.update({
    'auth_cluster_required': 'none',
    'auth_service_required': 'none',
    'auth_client_required': 'none' }) %}
{% endif %}
{% set conf = ceph.conf %}

include:
  - ceph.pkg

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
        {% for section, options in conf.iteritems() %}
        {% if not options %}
        {% continue %}
        {% endif %}
        {{ section }}:
            {% for key, value in options.iteritems() %}
            {{ key }}: '{{ value }}'
            {% endfor %}
        {% endfor %}
    - require:
      - file: ceph.conf.setup