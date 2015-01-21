{% from 'ceph/deploy/lookup.jinja' import ceph with context %}

{% set manage_repo = ceph.base.manage_repo | default(0) %}
{% set repos = ceph.base.repos | default({}) %}

{% if manage_repo %}
{% for repo in repos %}

ceph.repo.{{ repo.humanname }}.setup:
  pkgrepo.managed:
{% if grains['os_family'] in ['Debian', 'Deepin'] %}
    - name: {{ repo.name }}
    - humanname: {{ repo.humanname }}
    - dist: {{ repo.dist }}
    - file: {{ repo.file }}
    - key_url: {{ repo.key_url }}
{% elif grains['os_family'] in ['RedHat'] %}
    - name: {{ repo.name }}
    - humanname: {{ repo.humanname }}
    - baseurl: {{ repo.baseurl }}
    - gpgcheck: {{ repo.gpgcheck }}
    {% if repo.gpgcheck %}
    - gpgkey: {{ repo.gpgkey }}
    {% endif %}
{% endif %}

{% endfor %}
{% endif %}