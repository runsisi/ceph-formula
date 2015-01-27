{% from 'ceph/lookup.jinja' import ceph with context %}

{% set manage_repo = ceph.repo.manage_repo | default(0) %}
{% set repos = ceph.repo.repos | default({}) %}

{% if manage_repo %}
{% for repo in repos %}

ceph.repo.{{ repo.humanname }}.setup:
  pkgrepo.managed:
{% if grains['os_family'] in ['Debian',] %}
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