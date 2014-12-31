{% from "ceph/lookup.jinja" import ceph with context %}

{% if ceph.manage_repo %}
include:
  - ceph.repo
{% endif %}

ceph-pkg:
  pkg.installed:
    - names:
    {% for pkg in ceph.pkgs %}
      - {{ pkg }}
    {% endfor %}
    {% if ceph.manage_repo %}
    - require:
    {% if grains['os_family'] == 'Debian' or grains['os_family'] == 'Deepin' %}
      - pkgrepo: ceph-repo
    {% elif grains['os_family'] == 'RedHat' %}
      - pkgrepo: ceph-repo
      - pkgrepo: ceph-noarch-repo
    {% endif %}
    {% endif %}

ceph-config:
  file.managed:
    - name: /etc/ceph/{{ ceph.cluster }}.conf
    - source: salt://ceph/files/ceph.conf
    - template: jinja
    - makedirs: True
    - user: root
    - group: root
    - mode: 644