{% from 'ceph/lookup.jinja' import ceph with context %}

{% set cluster = ceph.cluster | default('ceph', True) %}

{% set auth_type = ceph.auth_type | default('none', True) %}
{% set mon_key = ceph.mon_key | default('', True) %}
{% set admin_key = ceph.admin_key | default('', True) %}
{% set bootstrap_osd_key = ceph.bootstrap_osd_key | default('', True) %}
{% set bootstrap_mds_key = ceph.bootstrap_mds_key | default('', True) %}

{% set mon_id = ceph.mon.mon_id | default(grains['id'], True) %}
{% set mon_addr = ceph.mon.mon_addr | default('', True) %}

include:
  - ceph.conf

{% if auth_type == 'cephx' %}
ceph.mon.dummy.files:
  file.managed:
    - names:
        - /etc/ceph/{{ cluster }}.client.admin.keyring
        - /var/lib/ceph/bootstrap-osd/{{ cluster }}.keyring
        - /var/lib/ceph/bootstrap-mds/{{ cluster }}.keyring
    - makedirs: True
    - replace: False
    - require:
      - ceph_conf: ceph.conf
    - require_in:
      - ceph_mon: ceph.mon
{% endif %}

ceph.mon:
  ceph_mon.present:
    - name: {{ mon_id }}
    - auth_type: {{ auth_type }}
    - mon_key: {{ mon_key }}
    - mon_addr: {{ mon_addr }}
    - cluster: {{ cluster }}
    - require:
      - ceph_conf: ceph.conf

ceph.mon.daemon:
  service.running:
    - name: ceph
    - enable: True
    - watch:
      - ceph_mon: ceph.mon
      - ceph_conf: ceph.conf

{% if auth_type == 'cephx' %}

{% if admin_key %}
ceph.client.admin.auth:
  ceph_key.auth_present:
    - name: client.admin
    - entity_key: {{ admin_key }}
    - admin_name: mon.
    - admin_key: {{ mon_key }}
    - mon_caps: allow *
    - osd_caps: allow *
    - mds_caps: allow
    - cluster: {{ cluster }}
    - require:
      - ceph_mon: ceph.mon.daemon

ceph.client.admin.keyring:
  ceph_key.keyring_present:
    - name: /etc/ceph/{{ cluster }}.client.admin.keyring
    - entity_name: client.admin
    - entity_key: {{ admin_key }}
    - require:
      - ceph_key: ceph.client.admin.auth
{% endif %}

{% if bootstrap_osd_key %}
ceph.client.bootstrap-osd.auth:
  ceph_key.auth_present:
    - name: client.bootstrap-osd
    - entity_key: {{ bootstrap_osd_key }}
    - admin_name: mon.
    - admin_key: {{ mon_key }}
    - mon_caps: allow profile bootstrap-osd
    - cluster: {{ cluster }}
    - require:
      - ceph_key: ceph.client.admin.keyring
{% endif %}

{% if bootstrap_mds_key %}
ceph.client.bootstrap-mds.auth:
  ceph_key.auth_present:
    - name: client.bootstrap-mds
    - entity_key: {{ bootstrap_mds_key }}
    - admin_name: mon.
    - admin_key: {{ mon_key }}
    - mon_caps: allow profile bootstrap-mds
    - cluster: {{ cluster }}
    - require:
      - ceph_key: ceph.client.admin.keyring
{% endif %}

{% endif %}
