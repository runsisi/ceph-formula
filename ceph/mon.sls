{% from "ceph/lookup.jinja" import config with context %}
{% from "ceph/lookup.jinja" import ceph with context %}

include:
  - ceph

{% if config.cluster != '' %}
{% set cluster_option = '--cluster ' ~ config.cluster %}
{% else %}
{% set cluster_option = '' %}
{% endif %}

{% if ceph.public_addr != '' %}
{% set public_addr_option = '--public_addr ' ~ ceph.public_addr %}
{% else %}
{% set public_addr_option = '' %}
{% endif %}

{% set mon_data = salt['cmd.run'](
    'ceph-mon ' ~ cluster_option ~ ' --id ' ~ ceph.mon_id 
    ~ ' --show-config-value mon_data') %}

{% if config.authentication_type == 'cephx' %}
{% if config.mon_key != '' %}
{% set keyring_path = '/tmp/' ~ config.cluster ~ '-mon-keyring' %}
ceph.mon.create.keyring:
  file.managed:
    - name: {{ keyring_path }}
    - mode: 444
    - contents: "[mon.]\n\tkey = {{ config.mon_key }}\n\tcaps mon = \"allow *\"\n"
    - require:
      - file: ceph.config
    - require_in:
      - cmd: ceph.mon.mkfs.{{ ceph.mon_id }}
{% elif config.mon_keyring != '' %}
{% set keyring_path = config.mon_keyring %}
{% endif %}
{% else %}
{% set keyring_path = '/dev/null' %}
{% endif %}

ceph.mon.mkfs.{{ ceph.mon_id }}:
  file.directory:
    - name: {{ mon_data }}
  cmd.run:
    - name: >
        ceph-mon {{ cluster_option }} {{ public_addr_option }}
        --mkfs --id {{ ceph.mon_id }} --keyring {{ keyring_path }}

ceph.mon.touch.dummy.files.{{ ceph.mon_id }}:
  file.managed:
    - names: 
        - /etc/ceph/{{ config.cluster }}.client.admin.keyring
        - {{ mon_data }}/done
        - {{ mon_data }}/sysvinit
        - {{ mon_data }}/keyring
    - replace: False
    - require:
      - cmd: ceph.mon.mkfs.{{ ceph.mon_id }}

ceph.mon.start.{{ ceph.mon_id }}:
  cmd.wait:
    - name: /etc/init.d/ceph {{ cluster_option }} restart mon.{{ ceph.mon_id }}
    - require:
      - file: ceph.mon.touch.dummy.files.{{ ceph.mon_id }}
    - onchanges:
      - file: ceph.config

{% if config.authentication_type == 'cephx' %}
{% if config.mon_key != '' %}
ceph.mon.delete.keyring:
  file.absent:
    - name: {{ keyring_path }}
    - require:
      - file: ceph.mon.create.keyring
{% endif %}
{% endif %}