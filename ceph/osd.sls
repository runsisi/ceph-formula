{% from 'ceph/lookup.jinja' import conf with context %}
{% from 'ceph/lookup.jinja' import osd with context %}

include:
  - ceph.conf

ceph.osd.keyring.create:
  file.managed:
    - name: /var/lib/ceph/bootstrap-osd/{{ conf.cluster }}.keyring
    - mode: 644
    - replace: False
    - require:
      - file: ceph.conf.setup
  cmd.run:
    - name: >
        ceph-authtool /var/lib/ceph/bootstrap-osd/{{ conf.cluster }}.keyring
        --name client.bootstrap-osd --add-key {{ conf.bootstrap_osd_key }}
        --cap mon 'allow profile bootstrap-osd'
    - unless: >
        ceph-authtool /var/lib/ceph/bootstrap-osd/{{ conf.cluster }}.keyring
        --name client.bootstrap-osd --print-key | grep {{ conf.bootstrap_osd_key }}
    - require:
      - file: ceph.osd.keyring.create

{% for osd in osd.osds %}
{% set data = osd['data'] %}
{% set journal = osd['journal'] if osd['journal'] is defined else '' %}

ceph.osd.{{ data }}.prepare:
  file.directory:
    - name: {{ data }}
    - makedirs: True
    - unless: ! test -b {{ data }}
  cmd.run:
    - name: >
        ceph-disk prepare --cluster {{ conf.cluster }}
        {{ data }} {{ journal }}
    - unless:
      - ceph-disk list | grep ' *{{ data }}.*ceph data, active'
      - ls -l /var/lib/ceph/osd/{{ conf.cluster }}-* | grep {{ data }}
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