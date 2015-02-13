{% from 'ceph/lookup.jinja' import ceph with context %}

{% set cluster = ceph.cluster | default('ceph', True) %}
{% set conf = '/etc/ceph/' + cluster + '.conf' %}

{% set auth_type = ceph.auth_type | default('none', True) %}
{% set mon_key = ceph.mon_key | default('', True) %}
{% set admin_key = ceph.admin_key | default('', True) %}
{% set bootstrap_osd_key = ceph.bootstrap_osd_key | default('', True) %}
{% set bootstrap_mds_key = ceph.bootstrap_mds_key | default('', True) %}

{% set mon_id = ceph.mon.mon_id | default(grains['id'], True) %}
{% set mon_addr = ceph.mon.mon_addr | default('', True) %}

include:
  - ceph.conf

ceph.mon.create:
  ceph_mon.present:
    - name: {{ mon_id }}
    - auth_type: {{ auth_type }}
    - mon_key: {{ mon_key }}
    - mon_addr: {{ mon_addr }}
    - cluster: {{ cluster }}
    - conf: {{ conf }}
    - require:
      - ini: ceph.conf.setup

ceph.mon.start:
  ceph_mon.running:
    - name: {{ mon_id }}
    - cluster: {{ cluster }}
    - conf: {{ conf }}
    - watch:
      - ceph_mon: ceph.mon.create
      - ini: ceph.conf.setup

{% if auth_type == 'cephx' %}

{% if admin_key and mon_key %}
ceph.client.admin.register:
  ceph_key.entity_present:
    - name: client.admin
    - entity_key: {{ admin_key }}
    - admin_name: mon.
    - admin_key: {{ mon_key }}
    - mon_caps: allow *
    - osd_caps: allow *
    - mds_caps: allow
    - cluster: {{ cluster }}
    - conf: {{ conf }}
    - require:
      - ceph_mon: ceph.mon.start
{% endif %}

{% if bootstrap_osd_key and mon_key %}
ceph.client.bootstrap-osd.register:
  ceph_key.entity_present:
    - name: client.bootstrap-osd
    - entity_key: {{ bootstrap_osd_key }}
    - admin_name: mon.
    - admin_key: {{ mon_key }}
    - mon_caps: allow profile bootstrap-osd
    - cluster: {{ cluster }}
    - conf: {{ conf }}
    - require:
      - ceph_mon: ceph.mon.start
{% endif %}

{% if bootstrap_mds_key and mon_key %}
ceph.client.bootstrap-mds.register:
  ceph_key.entity_present:
    - name: client.bootstrap-mds
    - entity_key: {{ bootstrap_mds_key }}
    - admin_name: mon.
    - admin_key: {{ mon_key }}
    - mon_caps: allow profile bootstrap-mds
    - cluster: {{ cluster }}
    - conf: {{ conf }}
    - require:
      - ceph_mon: ceph.mon.start
{% endif %}

{% endif %}
