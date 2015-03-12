{% from 'ceph/bootstrap/lookup.jinja' import bootstrap with context %}

{% set ntp = bootstrap.ntp %}

include:
  - ceph.bootstrap.repo

{% if grains['os_family'] == 'RedHat' %}
{% if grains['osmajorrelease'] == '7' %}
bootstrap.ntp.chronyd.stop:
  service.dead:
    - name: chronyd
    - enable: False
    - require_in:
      - pkg: bootstrap.ntp.pkg.install
{% endif %}
{% endif %}

bootstrap.ntp.pkg.install:
  pkg.installed:
    - name: {{ ntp.pkg }}

bootstrap.ntp.start:
  service.running:
    - name: {{ ntp.svc }}
    - enable: True
