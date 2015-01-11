{% from "ceph/lookup.jinja" import conf with context %}
{% from "ceph/lookup.jinja" import mon with context %}

include:
  - ceph.conf

{% set keyring_option = '--keyring /tmp/' + conf.cluster + '.mon.tmp.keyring'
    if conf.authentication_type == 'cephx' else ''
%}

{% set public_addr_option = '--public_addr ' + mon.public_addr
    if mon.public_addr is defined and mon.public_addr != '' else ''
%}

{% set mon_data_dir = mon.mon_data
    | replace('$name', '$type.$id')
    | replace('$cluster', conf.cluster)
    | replace('$type', 'mon')
    | replace('$id', mon.mon_id)
    | replace('$type', 'mon')
    | replace('$host',  salt['grains.get']('host'))
    if mon.mon_data is defined and mon.mon_data != ''
    else '/var/lib/ceph/mon/' + conf.cluster + '-' + mon.mon_id
%}

{% if conf.authentication_type == 'cephx' %}
ceph.mon.tmp.keyring.create:
  file.managed:
    - name: /tmp/{{ conf.cluster }}.mon.tmp.keyring
    - makedirs: True
    - mode: 644
    - replace: False
    - require:
      - file: ceph.conf.setup
    - unless:
      - test -f {{ mon_data_dir }}/keyring
  cmd.run:
    - name: >
        ceph-authtool /tmp/{{ conf.cluster }}.mon.tmp.keyring
        --name mon. --add-key {{ conf.mon_key }}
        --cap mon 'allow *'
    - unless: >
        ceph-authtool /tmp/{{ conf.cluster }}.mon.tmp.keyring
        --name mon. --print-key | grep {{ conf.mon_key }}
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
    - require:
      - file: ceph.conf.setup
  cmd.run:
    - name: >
        ceph-mon --cluster {{ conf.cluster }}
        --conf /etc/ceph/{{ conf.cluster }}.conf
        --mkfs --id {{ mon.mon_id }} {{ keyring_option }} {{ public_addr_option }}
    - creates: {{ mon_data_dir }}/done

ceph.mon.dummy.files.touch:
  file.managed:
    - names:
        - {{ mon_data_dir }}/done
        - {{ mon_data_dir }}/sysvinit
{% if conf.authentication_type == 'cephx' %}
        - /etc/ceph/{{ conf.cluster }}.client.admin.keyring
        - /var/lib/ceph/bootstrap-osd/{{ conf.cluster }}.keyring
        - /var/lib/ceph/bootstrap-mds/{{ conf.cluster }}.keyring
{% endif %}
    - makedirs: True
    - replace: False
    - require:
      - cmd: ceph.mon.mkfs

ceph.mon.restart:
  cmd.wait:
    - name: >
        /etc/init.d/ceph --cluster {{ conf.cluster }}
        --conf /etc/ceph/{{ conf.cluster }}.conf
        restart mon.{{ mon.mon_id }}
    - require:
      - file: ceph.mon.dummy.files.touch
    - watch:
      - file: ceph.conf.setup
      - cmd: ceph.mon.mkfs

ceph.mon.start:
  cmd.run:
    - name: >
        /etc/init.d/ceph --cluster {{ conf.cluster }}
        --conf /etc/ceph/{{ conf.cluster }}.conf
        start mon.{{ mon.mon_id }}
    - unless: >
        /etc/init.d/ceph --cluster {{ conf.cluster }}
        --conf /etc/ceph/{{ conf.cluster }}.conf
        status mon.{{ mon.mon_id }}
    - require:
      - file: ceph.mon.dummy.files.touch

{% if conf.authentication_type == 'cephx' %}
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
        --name mon. --add-key {{ conf.mon_key }}
        --cap mon 'allow *'
    - unless: >
        ceph-authtool {{ mon_data_dir }}/keyring
        --name mon. --print-key | grep {{ conf.mon_key }}
    - require:
      - file: ceph.mon.keyring.create

ceph.client.admin.keyring.create:
  file.managed:
    - name: /etc/ceph/{{ conf.cluster }}.client.admin.keyring
    - mode: 644
    - replace: False
    - require:
      - cmd: ceph.mon.start
      - cmd: ceph.mon.restart
  cmd.run:
    - name: >
        ceph-authtool /etc/ceph/{{ conf.cluster }}.client.admin.keyring
        --name client.admin --add-key {{ conf.admin_key }}
        --cap mon 'allow *' --cap osd 'allow *' --cap mds 'allow'
    - unless: >
        ceph-authtool /etc/ceph/{{ conf.cluster }}.client.admin.keyring
        --name client.admin --print-key | grep {{ conf.admin_key }}
    - require:
      - file: ceph.client.admin.keyring.create

ceph.client.admin.key.inject:
  cmd.run:
    - name: >
        ceph --cluster {{ conf.cluster }} --name mon.
        --keyring {{ mon_data_dir }}/keyring
        auth add client.admin --in-file /etc/ceph/{{ conf.cluster }}.client.admin.keyring
    - unless: >
        ceph --cluster {{ conf.cluster }} --name mon.
        --keyring {{ mon_data_dir }}/keyring
        auth get client.admin | grep {{ conf.admin_key }}
    - require:
      - cmd: ceph.client.admin.keyring.create

ceph.client.bootstrap-osd.keyring.create:
  file.managed:
    - name: /var/lib/ceph/bootstrap-osd/{{ conf.cluster }}.keyring
    - mode: 644
    - replace: False
    - require:
      - cmd: ceph.mon.start
      - cmd: ceph.mon.restart
  cmd.run:
    - name: >
        ceph-authtool /var/lib/ceph/bootstrap-osd/{{ conf.cluster }}.keyring
        --name client.bootstrap-osd --add-key {{ conf.bootstrap_osd_key }}
        --cap mon 'allow profile bootstrap-osd'
    - unless: >
        ceph-authtool /var/lib/ceph/bootstrap-osd/{{ conf.cluster }}.keyring
        --name client.bootstrap-osd --print-key | grep {{ conf.bootstrap_osd_key }}
    - require:
      - file: ceph.client.bootstrap-osd.keyring.create

ceph.client.bootstrap-osd.key.inject:
  cmd.run:
    - name: >
        ceph --cluster {{ conf.cluster }} --name mon.
        --keyring {{ mon_data_dir }}/keyring
        auth add client.bootstrap-osd --in-file /var/lib/ceph/bootstrap-osd/{{ conf.cluster }}.keyring
    - unless: >
        ceph --cluster {{ conf.cluster }} --name mon.
        --keyring {{ mon_data_dir }}/keyring
        auth get client.bootstrap-osd | grep {{ conf.bootstrap_osd_key }}
    - require:
      - cmd: ceph.client.bootstrap-osd.keyring.create

ceph.client.bootstrap-mds.keyring.create:
  file.managed:
    - name: /var/lib/ceph/bootstrap-mds/{{ conf.cluster }}.keyring
    - mode: 644
    - replace: False
    - require:
      - cmd: ceph.mon.start
      - cmd: ceph.mon.restart
  cmd.run:
    - name: >
        ceph-authtool /var/lib/ceph/bootstrap-mds/{{ conf.cluster }}.keyring
        --name client.bootstrap-mds --add-key {{ conf.bootstrap_mds_key }}
        --cap mon 'allow profile bootstrap-mds'
    - unless: >
        ceph-authtool /var/lib/ceph/bootstrap-mds/{{ conf.cluster }}.keyring
        --name client.bootstrap-mds --print-key | grep {{ conf.bootstrap_mds_key }}
    - require:
      - file: ceph.client.bootstrap-mds.keyring.create

ceph.client.bootstrap-mds.key.inject:
  cmd.run:
    - name: >
        ceph --cluster {{ conf.cluster }} --name mon.
        --keyring {{ mon_data_dir }}/keyring
        auth add client.bootstrap-mds --in-file /var/lib/ceph/bootstrap-mds/{{ conf.cluster }}.keyring
    - unless: >
        ceph --cluster {{ conf.cluster }} --name mon.
        --keyring {{ mon_data_dir }}/keyring
        auth get client.bootstrap-mds | grep {{ conf.bootstrap_mds_key }}
    - require:
      - cmd: ceph.client.bootstrap-mds.keyring.create

ceph.mon.tmp.keyring.delete:
  file.absent:
    - name: /tmp/{{ conf.cluster }}.mon.tmp.keyring
    - require:
      - file: ceph.mon.tmp.keyring.create
{% endif %}