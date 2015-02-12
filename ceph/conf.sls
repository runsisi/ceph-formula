{% from 'ceph/lookup.jinja' import ceph with context %}

{% set cluster = ceph.cluster | default('ceph', True) %}
{% set conf = '/etc/ceph/' + cluster + '.conf' %}

{% set auth_type = ceph.auth_type | default('cephx', True) %}

{% if auth_type == 'none' %}
{% do ceph.conf.global.update({
    'auth_cluster_required': 'none',
    'auth_service_required': 'none',
    'auth_client_required': 'none' }) %}
{% endif %}

{% set pkgs = ceph.pkg.pkgs | default({}) %}
{% set sections = ceph.conf %}

include:
  - ceph.pkg

ceph.conf.setup:
  file.managed:
    - name: {{ conf }}
    - makedirs: True
    - user: root
    - group: root
    - mode: 644
    - require:
      {% for pkg, ver in pkgs.iteritems() %}
      - pkg: ceph.pkg.{{ pkg }}.{{ ver }}.install
      {% endfor %}
  ini.sections_present:
    - name: {{ conf }}
    - sections:
        {% for section, options in sections.iteritems() %}
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
