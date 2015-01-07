{% from "ceph/lookup.jinja" import config with context %}
{% from "ceph/lookup.jinja" import ceph with context %}

include:
  - ceph

{% if config.authentication_type == 'cephx' %}
{% set keyring_option = '--keyring /tmp/' ~ config.cluster ~ '.mon.tmp.keyring' %}
{% else %}
{% set keyring_option = '' %}
{% endif %}

{% if ceph.public_addr != '' %}
{% set public_addr_option = '--public_addr ' ~ ceph.public_addr %}
{% else %}
{% set public_addr_option = '' %}
{% endif %}

{% set mon_data_dir = salt['cmd.run'](
    'ceph-mon --cluster ' ~ config.cluster ~ ' --id ' ~ ceph.mon_id 
    ~ ' --show-config-value mon_data') %}

{% if config.authentication_type == 'cephx' %}
ceph.mon.tmp.keyring.create:
  file.managed:
    - name: /tmp/{{ config.cluster }}.mon.tmp.keyring
    - makedirs: True
    - mode: 644
    - replace: False
    - require:
      - file: ceph.config
    - unless:
      - test -f {{ mon_data_dir }}/keyring
  cmd.run:
    - name: >
        ceph-authtool /tmp/{{ config.cluster }}.mon.tmp.keyring
        --name mon. --add-key {{ config.mon_key }}
        --cap mon 'allow *'
    - unless: >
        ceph-authtool /tmp/{{ config.cluster }}.mon.tmp.keyring
        --name mon. --print-key | grep {{ config.mon_key }}
    - creates: {{ mon_data_dir }}/keyring
    - require:
      - file: ceph.mon.tmp.keyring.create
    - require_in:
      - cmd: ceph.mon.mkfs
{% endif %}

ceph.mon.mkfs:
  file.directory:
    - name: {{ mon_data_dir }}
    - makedirs: True
  cmd.run:
    - name: >
        ceph-mon --cluster {{ config.cluster }}
        --conf /etc/ceph/{{ config.cluster }}.conf
        --mkfs --id {{ ceph.mon_id }} {{ keyring_option }} {{ public_addr_option }}
    - creates: {{ mon_data_dir }}/done

ceph.mon.dummy.files.touch:
  file.managed:
    - names:
        - {{ mon_data_dir }}/done
        - {{ mon_data_dir }}/sysvinit
{% if config.authentication_type == 'cephx' %}
        - /etc/ceph/{{ config.cluster }}.client.admin.keyring
        - /var/lib/ceph/bootstrap-osd/{{ config.cluster }}.keyring
        - /var/lib/ceph/bootstrap-mds/{{ config.cluster }}.keyring
{% endif %}
    - makedirs: True
    - replace: False
    - require:
      - cmd: ceph.mon.mkfs

ceph.mon.restart:
  cmd.wait:
    - name: >
        /etc/init.d/ceph --cluster {{ config.cluster }}
        --conf /etc/ceph/{{ config.cluster }}.conf
        restart mon.{{ ceph.mon_id }}
    - require:
      - file: ceph.mon.dummy.files.touch
    - watch:
      - file: ceph.config
      - cmd: ceph.mon.mkfs

ceph.mon.start:
  cmd.run:
    - name: >
        /etc/init.d/ceph --cluster {{ config.cluster }}
        --conf /etc/ceph/{{ config.cluster }}.conf
        start mon.{{ ceph.mon_id }}
    - unless: >
        /etc/init.d/ceph --cluster {{ config.cluster }}
        --conf /etc/ceph/{{ config.cluster }}.conf
        status mon.{{ ceph.mon_id }}
    - require:
      - file: ceph.mon.dummy.files.touch

{% if config.authentication_type == 'cephx' %}
ceph.mon.keyring.create:
  file.managed:
    - name: {{ mon_data_dir }}/keyring
    - mode: 644
    - replace: False
    - require:
      - file: ceph.mon.mkfs
    - require_in:
      - file: ceph.mon.dummy.files.touch
  cmd.run:
    - name: >
        ceph-authtool {{ mon_data_dir }}/keyring
        --name mon. --add-key {{ config.mon_key }}
        --cap mon 'allow *'
    - unless: >
        ceph-authtool {{ mon_data_dir }}/keyring
        --name mon. --print-key | grep {{ config.mon_key }}
    - require:
      - file: ceph.mon.keyring.create

ceph.client.admin.keyring.create:
  file.managed:
    - name: /etc/ceph/{{ config.cluster }}.client.admin.keyring
    - mode: 644
    - replace: False
    - require:
      - cmd: ceph.mon.start
      - cmd: ceph.mon.restart
  cmd.run:
    - name: >
        ceph-authtool /etc/ceph/{{ config.cluster }}.client.admin.keyring
        --name client.admin --add-key {{ config.admin_key }}
        --cap mon 'allow *' --cap osd 'allow *' --cap mds 'allow'
    - unless: >
        ceph-authtool /etc/ceph/{{ config.cluster }}.client.admin.keyring
        --name client.admin --print-key | grep {{ config.admin_key }}
    - require:
      - file: ceph.client.admin.keyring.create

ceph.client.admin.key.inject:
  cmd.run:
    - name: >
        ceph --cluster {{ config.cluster }} --name mon.
        --keyring {{ mon_data_dir }}/keyring
        auth add client.admin --in-file /etc/ceph/{{ config.cluster }}.client.admin.keyring
    - unless: >
        ceph --cluster {{ config.cluster }} --name mon.
        --keyring {{ mon_data_dir }}/keyring
        auth get client.admin | grep {{ config.admin_key }}
    - require:
      - cmd: ceph.client.admin.keyring.create

ceph.client.bootstrap-osd.keyring.create:
  file.managed:
    - name: /var/lib/ceph/bootstrap-osd/{{ config.cluster }}.keyring
    - mode: 644
    - replace: False
    - require:
      - cmd: ceph.mon.start
      - cmd: ceph.mon.restart
  cmd.run:
    - name: >
        ceph-authtool /var/lib/ceph/bootstrap-osd/{{ config.cluster }}.keyring
        --name client.bootstrap-osd --add-key {{ config.bootstrap_osd_key }}
        --cap mon 'allow profile bootstrap-osd'
    - unless: >
        ceph-authtool /var/lib/ceph/bootstrap-osd/{{ config.cluster }}.keyring
        --name client.bootstrap-osd --print-key | grep {{ config.bootstrap_osd_key }}
    - require:
      - file: ceph.client.bootstrap-osd.keyring.create

ceph.client.bootstrap-osd.key.inject:
  cmd.run:
    - name: >
        ceph --cluster {{ config.cluster }} --name mon.
        --keyring {{ mon_data_dir }}/keyring
        auth add client.bootstrap-osd --in-file /var/lib/ceph/bootstrap-osd/{{ config.cluster }}.keyring
    - unless: >
        ceph --cluster {{ config.cluster }} --name mon.
        --keyring {{ mon_data_dir }}/keyring
        auth get client.bootstrap-osd | grep {{ config.bootstrap_osd_key }}
    - require:
      - cmd: ceph.client.bootstrap-osd.keyring.create

ceph.client.bootstrap-mds.keyring.create:
  file.managed:
    - name: /var/lib/ceph/bootstrap-mds/{{ config.cluster }}.keyring
    - mode: 644
    - replace: False
    - require:
      - cmd: ceph.mon.start
      - cmd: ceph.mon.restart
  cmd.run:
    - name: >
        ceph-authtool /var/lib/ceph/bootstrap-mds/{{ config.cluster }}.keyring
        --name client.bootstrap-mds --add-key {{ config.bootstrap_mds_key }}
        --cap mon 'allow profile bootstrap-mds'
    - unless: >
        ceph-authtool /var/lib/ceph/bootstrap-mds/{{ config.cluster }}.keyring
        --name client.bootstrap-mds --print-key | grep {{ config.bootstrap_mds_key }}
    - require:
      - file: ceph.client.bootstrap-mds.keyring.create

ceph.client.bootstrap-mds.key.inject:
  cmd.run:
    - name: >
        ceph --cluster {{ config.cluster }} --name mon.
        --keyring {{ mon_data_dir }}/keyring
        auth add client.bootstrap-mds --in-file /var/lib/ceph/bootstrap-mds/{{ config.cluster }}.keyring
    - unless: >
        ceph --cluster {{ config.cluster }} --name mon.
        --keyring {{ mon_data_dir }}/keyring
        auth get client.bootstrap-mds | grep {{ config.bootstrap_mds_key }}
    - require:
      - cmd: ceph.client.bootstrap-mds.keyring.create

ceph.mon.tmp.keyring.delete:
  file.absent:
    - name: /tmp/{{ config.cluster }}.mon.tmp.keyring
    - require:
      - file: ceph.mon.tmp.keyring.create
{% endif %}