{% from 'ceph/lookup.jinja' import ceph with context %}

{% set ntp = ceph.ntp %}

{% if grains['os_family'] == 'RedHat' %}
{% if grains['osmajorrelease'] == '7' %}
ceph.ntp.stop.chronyd:
  service.dead:
    - name: chronyd
    - enable: False
    - require_in:
      - pkg: ceph.ntp.pkg.install
{% endif %}
{% endif %}

ceph.ntp.pkg.install:
  pkg.installed:
    - name: {{ ntp.pkg }}

ceph.ntp.conf.setup:
  file.managed:
    - name: {{ ntp.conf }}
    - source: salt://ceph/files/ntp.conf
    - template: jinja
    - context:
        ntp: {{ ntp }}
    - require:
      - pkg: ceph.ntp.pkg.install

ceph.ntp.start:
  service.running:
    - name: {{ ntp.svc }}
    - enable: True
    - watch:
      - file: ceph.ntp.conf.setup