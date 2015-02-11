{% from 'ceph/lookup.jinja' import ceph with context %}

{% set cluster = ceph.cluster | default('ceph', True) %}
{% set conf = '/etc/ceph/' + cluster + '.conf' %}

{% set auth_type = ceph.auth_type | default('cephx', True) %}
{% set bootstrap_osd_key = ceph.bootstrap_osd_key | default('', True) %}

{% set osds = ceph.osd.osds | default({}) %}

include:
  - ceph.conf

ceph.osd.keyring.create:
  ceph_key.keyring_present:
    - name: /var/lib/ceph/bootstrap-osd/{{ cluster }}.keyring
    - entity_name: client.bootstrap-osd
    - entity_key: {{ bootstrap_osd_key }}

{% for osd in osds %}
{% set data = osd['data'] %}
{% set journal = osd['journal'] | default('') %}

ceph.osd.{{ data }}.prepare:
  file.directory:
    - name: {{ data }}
    - makedirs: True
    - unless: ! test -b {{ data }}
  cmd.run:
    - name: >
        ceph-disk prepare --cluster {{ cluster }}
        {{ data }} {{ journal }}
    - unless:
      - ceph-disk list | grep ' *{{ data }}.*ceph data, active'
      - ls -l /var/lib/ceph/osd/{{ cluster }}-* | grep {{ data }}
    - require:
      - file: ceph.osd.{{ data }}.prepare

ceph.osd.{{ data }}.activate:
  cmd.run:
    - name: >
        ceph-disk activate {{ data }}
    - unless: test -b {{ data }}
    - require:
      - cmd: ceph.osd.{{ data }}.prepare

{% endfor %}
