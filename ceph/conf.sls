{% from 'ceph/lookup.jinja' import ceph with context %}

{% set cluster = ceph.cluster | default('ceph', True) %}
{% set auth_type = ceph.auth_type | default('none', True) %}

{% if auth_type != 'cephx' %}
{% do ceph.ceph_config.global.update({
    'auth_cluster_required': 'none',
    'auth_service_required': 'none',
    'auth_client_required': 'none' }) %}
{% endif %}

include:
  - ceph.pkg

ceph.conf:
  ceph_conf.present:
    - ctx: {{ ceph.ceph_config }}
    - cluster: {{ cluster }}
    - require:
      - pkg: ceph.pkg
