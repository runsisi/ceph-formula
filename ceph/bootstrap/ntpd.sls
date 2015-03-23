{% from 'ceph/bootstrap/lookup.jinja' import bootstrap with context %}

{% set ntp = bootstrap.ntp %}

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

bootstrap.ntp.conf.setup:
  file.managed:
    - name: {{ ntp.cfile }}
    - source: salt://ceph/bootstrap/files/ntpd.conf
    - template: jinja
    - context:
        ntp: {{ ntp }}
    - require:
      - pkg: bootstrap.ntp.pkg.install

bootstrap.ntp.start:
  service.running:
    - name: {{ ntp.svc }}
    - enable: True
    - watch:
      - file: bootstrap.ntp.conf.setup
