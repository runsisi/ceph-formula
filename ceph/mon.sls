{% from 'ceph/lookup.jinja' import ceph with context %}

{% set cluster = ceph.cluster | default('') | trim | default('ceph', True) %}
{% set mon_key = ceph.mon_key %}
{% set admin_key = ceph.admin_key %}
{% set bootstrap_osd_key = ceph.bootstrap_osd_key %}
{% set bootstrap_mds_key = ceph.bootstrap_mds_key %}
{% set auth_type = ceph.auth_type | default('') | trim | default('cephx', True) %}
{% set mon_id = ceph.mon.mon_id | default(grains['id']) %}
{% set mon_data = ceph.conf.mon.mon_data | default('') | trim | default('/var/lib/ceph/mon/$cluster-$id', True) %}
{% set mon_data = mon_data
    | replace('$name', '$type.$id')
    | replace('$cluster', cluster)
    | replace('$type', 'mon')
    | replace('$id', mon_id)
    | replace('$host',  salt['grains.get']('host')) %}
{% set public_addr = ceph.conf.mon.public_addr | default('') | trim | default('', True) %}
{% set keyring_option = '--keyring /tmp/' + cluster + '.mon.tmp.keyring' if auth_type == 'cephx' else '' %}
{% set public_addr_option = '--public_addr ' + public_addr if public_addr else '' %}

include:
  - ceph.conf

{% if auth_type != 'none' %}
ceph.mon.tmp.keyring.create:
  file.managed:
    - name: /tmp/{{ cluster }}.mon.tmp.keyring
    - makedirs: True
    - mode: 644
    - replace: False
    - require:
      - file: ceph.conf.setup
    - unless:
      - test -f {{ mon_data }}/keyring
  cmd.run:
    - name: >
        ceph-authtool /tmp/{{ cluster }}.mon.tmp.keyring
        --name mon. --add-key {{ mon_key }}
        --cap mon 'allow *'
    - unless: >
        ceph-authtool /tmp/{{ cluster }}.mon.tmp.keyring
        --name mon. --print-key | grep {{ mon_key }}
    - creates: {{ mon_data }}/keyring
    - require:
      - file: ceph.mon.tmp.keyring.create
    - require_in:
      - cmd: ceph.mon.mkfs
{% endif %}

ceph.mon.mkfs:
  file.directory:
    - name: {{ mon_data }}
    - makedirs: True
    - require:
      - file: ceph.conf.setup
  cmd.run:
    - name: >
        ceph-mon --cluster {{ cluster }}
        --conf /etc/ceph/{{ cluster }}.conf
        --mkfs --id {{ mon_id }} {{ keyring_option }} {{ public_addr_option }}
    - creates: {{ mon_data }}/done

ceph.mon.dummy.files.touch:
  file.managed:
    - names:
        - {{ mon_data }}/done
        - {{ mon_data }}/sysvinit
{% if auth_type == 'cephx' %}
        - /etc/ceph/{{ cluster }}.client.admin.keyring
        - /var/lib/ceph/bootstrap-osd/{{ cluster }}.keyring
        - /var/lib/ceph/bootstrap-mds/{{ cluster }}.keyring
{% endif %}
    - makedirs: True
    - replace: False
    - require:
      - cmd: ceph.mon.mkfs

ceph.mon.restart:
  cmd.wait:
    - name: >
        /etc/init.d/ceph --cluster {{ cluster }}
        --conf /etc/ceph/{{ cluster }}.conf
        restart mon.{{ mon_id }}
    - require:
      - file: ceph.mon.dummy.files.touch
    - watch:
      - file: ceph.conf.setup
      - cmd: ceph.mon.mkfs

ceph.mon.start:
  cmd.run:
    - name: >
        /etc/init.d/ceph --cluster {{ cluster }}
        --conf /etc/ceph/{{ cluster }}.conf
        start mon.{{ mon_id }}
    - unless: >
        /etc/init.d/ceph --cluster {{ cluster }}
        --conf /etc/ceph/{{ cluster }}.conf
        status mon.{{ mon_id }}
    - require:
      - file: ceph.mon.dummy.files.touch

{% if auth_type != 'none' %}
ceph.mon.keyring.create:
  file.managed:
    - name: {{ mon_data }}/keyring
    - mode: 644
    - replace: False
    - require:
      - file: ceph.mon.mkfs
    - require_in:
      - file: ceph.mon.dummy.files.touch
  cmd.run:
    - name: >
        ceph-authtool {{ mon_data }}/keyring
        --name mon. --add-key {{ mon_key }}
        --cap mon 'allow *'
    - unless: >
        ceph-authtool {{ mon_data }}/keyring
        --name mon. --print-key | grep {{ mon_key }}
    - require:
      - file: ceph.mon.keyring.create

ceph.client.admin.keyring.create:
  file.managed:
    - name: /etc/ceph/{{ cluster }}.client.admin.keyring
    - mode: 644
    - replace: False
    - require:
      - cmd: ceph.mon.start
      - cmd: ceph.mon.restart
  cmd.run:
    - name: >
        ceph-authtool /etc/ceph/{{ cluster }}.client.admin.keyring
        --name client.admin --add-key {{ admin_key }}
        --cap mon 'allow *' --cap osd 'allow *' --cap mds 'allow'
    - unless: >
        ceph-authtool /etc/ceph/{{ cluster }}.client.admin.keyring
        --name client.admin --print-key | grep {{ admin_key }}
    - require:
      - file: ceph.client.admin.keyring.create

ceph.client.admin.key.inject:
  cmd.run:
    - name: >
        ceph --cluster {{ cluster }} --name mon.
        --keyring {{ mon_data }}/keyring
        auth add client.admin --in-file /etc/ceph/{{ cluster }}.client.admin.keyring
    - unless: >
        ceph --cluster {{ cluster }} --name mon.
        --keyring {{ mon_data }}/keyring
        auth get client.admin | grep {{ admin_key }}
    - require:
      - cmd: ceph.client.admin.keyring.create

ceph.client.bootstrap-osd.keyring.create:
  file.managed:
    - name: /var/lib/ceph/bootstrap-osd/{{ cluster }}.keyring
    - mode: 644
    - replace: False
    - require:
      - cmd: ceph.mon.start
      - cmd: ceph.mon.restart
  cmd.run:
    - name: >
        ceph-authtool /var/lib/ceph/bootstrap-osd/{{ cluster }}.keyring
        --name client.bootstrap-osd --add-key {{ bootstrap_osd_key }}
        --cap mon 'allow profile bootstrap-osd'
    - unless: >
        ceph-authtool /var/lib/ceph/bootstrap-osd/{{ cluster }}.keyring
        --name client.bootstrap-osd --print-key | grep {{ bootstrap_osd_key }}
    - require:
      - file: ceph.client.bootstrap-osd.keyring.create

ceph.client.bootstrap-osd.key.inject:
  cmd.run:
    - name: >
        ceph --cluster {{ cluster }} --name mon.
        --keyring {{ mon_data }}/keyring
        auth add client.bootstrap-osd --in-file /var/lib/ceph/bootstrap-osd/{{ cluster }}.keyring
    - unless: >
        ceph --cluster {{ cluster }} --name mon.
        --keyring {{ mon_data }}/keyring
        auth get client.bootstrap-osd | grep {{ bootstrap_osd_key }}
    - require:
      - cmd: ceph.client.bootstrap-osd.keyring.create

ceph.client.bootstrap-mds.keyring.create:
  file.managed:
    - name: /var/lib/ceph/bootstrap-mds/{{ cluster }}.keyring
    - mode: 644
    - replace: False
    - require:
      - cmd: ceph.mon.start
      - cmd: ceph.mon.restart
  cmd.run:
    - name: >
        ceph-authtool /var/lib/ceph/bootstrap-mds/{{ cluster }}.keyring
        --name client.bootstrap-mds --add-key {{ bootstrap_mds_key }}
        --cap mon 'allow profile bootstrap-mds'
    - unless: >
        ceph-authtool /var/lib/ceph/bootstrap-mds/{{ cluster }}.keyring
        --name client.bootstrap-mds --print-key | grep {{ bootstrap_mds_key }}
    - require:
      - file: ceph.client.bootstrap-mds.keyring.create

ceph.client.bootstrap-mds.key.inject:
  cmd.run:
    - name: >
        ceph --cluster {{ cluster }} --name mon.
        --keyring {{ mon_data }}/keyring
        auth add client.bootstrap-mds --in-file /var/lib/ceph/bootstrap-mds/{{ cluster }}.keyring
    - unless: >
        ceph --cluster {{ cluster }} --name mon.
        --keyring {{ mon_data }}/keyring
        auth get client.bootstrap-mds | grep {{ bootstrap_mds_key }}
    - require:
      - cmd: ceph.client.bootstrap-mds.keyring.create

ceph.mon.tmp.keyring.delete:
  file.absent:
    - name: /tmp/{{ cluster }}.mon.tmp.keyring
    - require:
      - file: ceph.mon.tmp.keyring.create
{% endif %}