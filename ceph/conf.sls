{% from "ceph/lookup.jinja" import conf with context %}

include:
  - ceph.pkg

ceph.conf.setup:
  file.managed:
    - name: /etc/ceph/{{ conf.cluster }}.conf
    - makedirs: True
    - user: root
    - group: root
    - mode: 644
    - require:
      - pkg: ceph.pkg.install
  ini.sections_present:
    - name: /etc/ceph/{{ conf.cluster }}.conf
    - sections:
        {% if conf.global is defined and conf.global is not none %}
        global:
          {% for key, value in conf.global.iteritems() %}
          {{ key }}: '{{ value }}'
          {% endfor %}
        {% endif %}
        {% if conf.mon is defined and conf.mon is not none %}
        mon:
          {% for key, value in conf.mon.iteritems() %}
          {{ key }}: '{{ value }}'
          {% endfor %}
        {% endif %}
        {% if conf.osd is defined and conf.osd is not none  %}
        osd:
          {% for key, value in conf.osd.iteritems() %}
          {{ key }}: '{{ value }}'
          {% endfor %}
        {% endif %}
    - require:
      - file: ceph.conf.setup
      
ceph.conf.cleanup:
  ini.sections_absent:
    - name: /etc/ceph/{{ conf.cluster }}.conf
    - sections:
      - {{ 'global' if conf.global is not defined or conf.global is none else '' }}
      - {{ 'mon' if conf.mon is not defined or conf.mon is none else '' }}
      - {{ 'osd' if conf.osd is not defined or conf.osd is none else '' }}
    - require:
      - ini: ceph.conf.setup