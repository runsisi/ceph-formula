{% from 'ceph/lookup.jinja' import ceph with context %}

{% set cluster = ceph.cluster | default('ceph', True) %}
{% set auth_type = ceph.auth_type | default('none', True) %}
{% set pkgs = ceph.pkg.pkgs | default({}, True) %}

{% if auth_type != 'cephx' %}
{% do ceph.conf.global.update({
    'auth_cluster_required': 'none',
    'auth_service_required': 'none',
    'auth_client_required': 'none' }) %}
{% endif %}

include:
  - ceph.pkg

ceph.conf.setup:
  ceph_conf.present:
    - ctx: {{ ceph.conf }}
    - cluster: {{ cluster }}
    {% if pkgs %}
    - require:
      {% for pkg, ver in pkgs.iteritems() %}
      - pkg: ceph.pkg.{{ pkg }}.{{ ver }}.install
      {% endfor %}
    {% endif %}
