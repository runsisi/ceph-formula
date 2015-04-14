{% from 'ceph/lookup.jinja' import ceph with context %}

{% set srvs = ceph.ntp_servers %}

{% if grains['os_family'] == 'RedHat' %}
{% if grains['osmajorrelease'] == '7' %}
ceph.ntp.chronyd:
  service.dead:
    - name: chronyd
    - enable: False
    - require_in:
      - pkg: ceph.ntp.pkg
{% endif %}
{% endif %}

ceph.ntp.pkg:
  pkg.installed:
    - name: ntp

ceph.ntp.conf:
  file.managed:
    - name: /etc/ntp.conf
    - source: salt://ceph/files/ntpd.conf
    - template: jinja
    - context:
        srvs: {{ srvs }}
    - require:
      - pkg: ceph.ntp.pkg

ceph.ntp.daemon:
  service.running:
    - name: ntpd
    - enable: True
    - watch:
      - file: ceph.ntp.conf
