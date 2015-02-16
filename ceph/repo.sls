{% from 'ceph/lookup.jinja' import ceph with context %}

{% set manage_repo = ceph.repo.manage_repo | default(0, True) %}
{% set repos = ceph.repo.repos | default({}, True) %}

{% if manage_repo %}
{% for repo in repos %}

ceph.repo.{{ repo.humanname }}.setup:
  pkgrepo.managed:
{% if grains['os_family'] in ['Debian',] %}
    {% set key_url = repo.key_url | default('') | trim %}
    {% set ppa = repo.ppa | default('') | trim %}
    - name: {{ repo.name }}
    - humanname: {{ repo.humanname }}
    - dist: {{ repo.dist }}
    - file: {{ repo.file }}
    {% if key_url %}
    - key_url: {{ repo.key_url }}
    {% endif %}
    {% if ppa %}
    - ppa: {{ ppa }}
    {% endif %}
{% elif grains['os_family'] in ['RedHat'] %}
    {% set gpgkey = repo.gpgkey | default('') | trim %}
    - name: {{ repo.name }}
    - humanname: {{ repo.humanname }}
    - baseurl: {{ repo.baseurl }}
    - gpgcheck: {{ repo.gpgcheck }}
    {% if repo.gpgcheck and gpgkey %}
    - gpgkey: {{ gpgkey }}
    {% endif %}
{% endif %}

{% endfor %}
{% endif %}
