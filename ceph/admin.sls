{% from 'ceph/lookup.jinja' import ceph with context %}

{% set cluster = ceph.cluster | default('ceph', True) %}
{% set auth_type = ceph.auth_type | default('none', True) %}
{% set admin_key = ceph.admin_key | default('', True) %}

include:
  - ceph.conf

{% if auth_type == 'cephx' %}
ceph.client.admin.keyring:
  ceph_key.keyring_present:
    - name: /etc/ceph/{{ cluster }}.client.admin.keyring
    - entity_name: client.admin
    - entity_key: {{ admin_key }}
{% endif %}
