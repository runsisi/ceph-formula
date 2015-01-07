{% from "ceph/lookup.jinja" import config with context %}
{% from "ceph/lookup.jinja" import ceph with context %}

include:
  - ceph

ceph.osd.keyring.create:
  file.managed:
    - name: /var/lib/ceph/bootstrap-osd/{{ config.cluster }}.keyring
    - mode: 644
    - replace: False
    - require:
      - file: ceph.config
  cmd.run:
    - name: >
        ceph-authtool /var/lib/ceph/bootstrap-osd/{{ config.cluster }}.keyring
        --name client.bootstrap-osd --add-key {{ config.bootstrap_osd_key }}
        --cap mon 'allow profile bootstrap-osd'
    - unless: >
        ceph-authtool /var/lib/ceph/bootstrap-osd/{{ config.cluster }}.keyring
        --name client.bootstrap-osd --print-key | grep {{ config.bootstrap_osd_key }}
    - require:
      - file: ceph.osd.keyring.create

{% for osd in ceph.osds %}
{% set data = osd['data'] %}
{% set journal = osd['journal'] if osd['journal'] is defined else '' %}

ceph.osd.{{ data }}.prepare:
  file.directory:
    - name: {{ data }}
    - makedirs: True
    - unless: ! test -b {{ data }}
  cmd.run:
    - name: >
        ceph-disk prepare --cluster {{ config.cluster }}
        {{ data }} {{ journal }}
    - unless:
      - ceph-disk list | grep ' *{{ data }}.*ceph data, active'
      - ls -l /var/lib/ceph/osd/{{ config.cluster }}-* | grep {{ data }}
    - require:
      - file: ceph.osd.{{ data }}.prepare

ceph.osd.{{ data }}.activate:
  cmd.wait:
    - name: >
        ceph-disk activate {{ data }}
    - unless: ! test -b {{ data }}
    - watch:
      - cmd: ceph.osd.{{ data }}.prepare
{% endfor %}