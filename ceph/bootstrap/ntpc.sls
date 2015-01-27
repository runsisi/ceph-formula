{% from 'ceph/bootstrap/lookup.jinja' import bootstrap with context %}

{% set ntp = bootstrap.ntp %}

include:
  - ceph.bootstrap.ntp

bootstrap.ntp.conf.setup:
  file.managed:
    - name: {{ ntp.cfile }}
    - source: salt://ceph/bootstrap/files/ntpc.conf
    - template: jinja
    - context:
        ntp: {{ ntp }}
    - require_in:
      - service: bootstrap.ntp.start
    - require:
      - pkg: bootstrap.ntp.pkg.install