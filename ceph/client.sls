{% from 'ceph/lookup.jinja' import conf with context %}

include:
  - ceph.conf

ceph.client.keyring.create:
  file.managed:
    - name: /etc/ceph/{{ conf.cluster }}.client.admin.keyring
    - mode: 644
    - replace: False
    - require:
      - file: ceph.conf.setup
  cmd.run:
    - name: >
        ceph-authtool /etc/ceph/{{ conf.cluster }}.client.admin.keyring
        --name client.admin --add-key {{ conf.admin_key }}
        --cap mon 'allow *' --cap osd 'allow *' --cap mds 'allow'
    - unless: >
        ceph-authtool /etc/ceph/{{ conf.cluster }}.client.admin.keyring
        --name client.admin --print-key | grep {{ conf.admin_key }}
    - require:
      - file: ceph.client.keyring.create