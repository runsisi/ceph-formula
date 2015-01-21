{% from 'ceph/deploy/lookup.jinja' import ceph with context %}

{% set cluster = ceph.conf.cluster | default('') | trim | default('ceph', True) %}
{% set admin_key = ceph.conf.admin_key %}

include:
  - ceph.deploy.conf

ceph.client.keyring.create:
  file.managed:
    - name: /etc/ceph/{{ cluster }}.client.admin.keyring
    - mode: 644
    - replace: False
    - require:
      - file: ceph.conf.setup
  cmd.run:
    - name: >
        ceph-authtool /etc/ceph/{{ cluster }}.client.admin.keyring
        --name client.admin --add-key {{ admin_key }}
        --cap mon 'allow *' --cap osd 'allow *' --cap mds 'allow'
    - unless: >
        ceph-authtool /etc/ceph/{{ cluster }}.client.admin.keyring
        --name client.admin --print-key | grep {{ admin_key }}
    - require:
      - file: ceph.client.keyring.create