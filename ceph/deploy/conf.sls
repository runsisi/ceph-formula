{% from 'ceph/deploy/lookup.jinja' import ceph with context %}

{% set pkgs = ceph.base.pkgs | default({}) %}
{% set cluster = ceph.cluster | default('') | trim | default('ceph', True) %}
{% set auth_type = ceph.auth_type | default('') | trim | default('cephx', True) %}
{% if auth_type == 'none' %}
{% do ceph.conf.global.update({
    'auth_cluster_required': 'none',
    'auth_service_required': 'none',
    'auth_client_required': 'none' }) %}
{% endif %}

include:
  - ceph.deploy.pkg

ceph.conf.setup:
  file.managed:
    - name: /etc/ceph/{{ cluster }}.conf
    - source: salt://ceph/deploy/files/ceph.conf
    - template: jinja
    - makedirs: True
    - user: root
    - group: root
    - mode: 644
    - require:
      {% for pkg, ver in pkgs.iteritems() %}
      - pkg: ceph.pkg.{{ pkg }}.{{ ver }}.install
      {% endfor %}
    - context:
        ceph: {{ ceph }}