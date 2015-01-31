{% from 'ceph/lookup.jinja' import ceph with context %}

{% set cluster = ceph.cluster | default('') | trim | default('ceph', True) %}
{% set bootstrap_osd_key = ceph.bootstrap_osd_key %}
{% set osds = ceph.osd.osds | default({}) %}

include:
  - ceph.conf

ceph.osd.keyring.create:
  file.managed:
    - name: /var/lib/ceph/bootstrap-osd/{{ cluster }}.keyring
    - mode: 644
    - replace: False
    - require:
      - ini: ceph.conf.setup
  cmd.run:
    - name: >
        ceph-authtool /var/lib/ceph/bootstrap-osd/{{ cluster }}.keyring
        --name client.bootstrap-osd --add-key {{ bootstrap_osd_key }}
        --cap mon 'allow profile bootstrap-osd'
    - unless: >
        ceph-authtool /var/lib/ceph/bootstrap-osd/{{ cluster }}.keyring
        --name client.bootstrap-osd --print-key | grep {{ bootstrap_osd_key }}
    - require:
      - file: ceph.osd.keyring.create

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