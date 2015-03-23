{% from 'ceph/lookup.jinja' import ceph with context %}

{% set cluster = ceph.cluster | default('ceph', True) %}

{% set auth_type = ceph.auth_type | default('none', True) %}
{% set admin_key = ceph.admin_key | default('', True) %}
{% set bootstrap_osd_key = ceph.bootstrap_osd_key | default('', True) %}

{% set osds = ceph.osd.osds | default({}, True) %}

include:
  - ceph.conf

{% if auth_type == 'cephx' %}
ceph.osd.keyring.create:
  ceph_key.keyring_present:
    - name: /var/lib/ceph/bootstrap-osd/{{ cluster }}.keyring
    - entity_name: client.bootstrap-osd
    - entity_key: {{ bootstrap_osd_key }}

ceph.client.admin.keyring.create:
  ceph_key.keyring_present:
    - name: /etc/ceph/{{ cluster }}.client.admin.keyring
    - entity_name: client.admin
    - entity_key: {{ admin_key }}
    - require:
      - ceph_key: ceph.osd.keyring.create
{% endif %}

{% for osd in osds %}
{% set data = osd['data'] %}
{% set journal = osd['journal'] | default('') %}

ceph.osd.{{ data }}.create:
  ceph_osd.present:
    - name: {{ data }}
    - journal: {{ journal }}
    - cluster: {{ cluster }}
    {% if auth_type == 'cephx' %}
    - require:
      - ceph_key: ceph.osd.keyring.create
    {% endif %}
    - require_in:
      - service: ceph.service.enable

{% endfor %}

ceph.service.enable:
  service.running:
    - name: ceph
    - enable: True
    {% if auth_type == 'cephx' %}
    - requre:
      ceph_key: ceph.osd.keyring.create
    {% endif %}
    - watch:
      - ceph_conf: ceph.conf.setup
