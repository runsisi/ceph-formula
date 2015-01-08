{% from "ceph/lookup.jinja" import config with context %}

include:
  - ceph

ceph.client.keyring.create:
  file.managed:
    - name: /etc/ceph/{{ config.cluster }}.client.admin.keyring
    - mode: 644
    - replace: False
    - require:
      - file: ceph.config
  cmd.run:
    - name: >
        ceph-authtool /etc/ceph/{{ config.cluster }}.client.admin.keyring
        --name client.admin --add-key {{ config.admin_key }}
        --cap mon 'allow *' --cap osd 'allow *' --cap mds 'allow'
    - unless: >
        ceph-authtool /etc/ceph/{{ config.cluster }}.client.admin.keyring
        --name client.admin --print-key | grep {{ config.admin_key }}
    - require:
      - file: ceph.client.keyring.create