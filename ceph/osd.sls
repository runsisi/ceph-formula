{% from 'ceph/lookup.jinja' import ceph with context %}

{% set cluster = ceph.cluster | default('ceph', True) %}

{% set auth_type = ceph.auth_type | default('none', True) %}
{% set admin_key = ceph.admin_key | default('', True) %}
{% set bootstrap_osd_key = ceph.bootstrap_osd_key | default('', True) %}

{% set osds = ceph.osds | default({}, True) %}

include:
  - ceph.conf

{% if auth_type == 'cephx' %}
ceph.bootstrap-osd.keyring:
  ceph_key.keyring_present:
    - name: /var/lib/ceph/bootstrap-osd/{{ cluster }}.keyring
    - entity_name: client.bootstrap-osd
    - entity_key: {{ bootstrap_osd_key }}
ceph.client.admin.keyring:
  ceph_key.keyring_present:
    - name: /etc/ceph/{{ cluster }}.client.admin.keyring
    - entity_name: client.admin
    - entity_key: {{ admin_key }}
{% endif %}

{% for data, journal in osds.iteritems() %}
{% set journal = journal if journal != None else '' %}

ceph.osd.{{ data }}:
  ceph_osd.present:
    - name: {{ data }}
    - journal: {{ journal }}
    - cluster: {{ cluster }}
    {% if auth_type == 'cephx' %}
    - require:
      - ceph_key: ceph.bootstrap-osd.keyring
    {% endif %}
    - require_in:
      - service: ceph.osd.service

{% endfor %}

ceph.osd.service:
  service.enabled:
    - name: ceph
