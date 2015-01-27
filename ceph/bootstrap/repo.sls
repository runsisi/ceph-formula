{% from 'ceph/bootstrap/lookup.jinja' import bootstrap with context %}

{% set cleanup = bootstrap.repo.cleanup | default(0) %}
{% set repos = bootstrap.repo.repos | default({}) %}

{% if cleanup %}
{% if grains['os_family'] in ['Debian',] %}
ceph.bootstrap.repo.cleanup.1:
  file.managed:
    - name: /etc/apt/sources.list
    - contents: ' '
ceph.bootstrap.repo.cleanup.2:
  file.directory:
    - name: /etc/apt/sources.list.d
    - clean: True
{% elif grains['os_family'] in ['RedHat'] %}
ceph.bootstrap.repo.cleanup:
  file.directory:
    - name: /etc/yum.repos.d
    - clean: True
{% endif %}
{% endif %}

{% for repo in repos %}

ceph.bootstrap.repo.{{ repo.humanname }}.setup:
  pkgrepo.managed:
{% if grains['os_family'] in ['Debian',] %}
    {% with key_url = repo.key_url | default('') | trim %}
    {% with ppa = repo.ppa | default('') | trim %}
    - name: {{ repo.name }}
    - humanname: {{ repo.humanname }}
    - dist: {{ repo.dist }}
    - file: {{ repo.file }}
    {% if key_url %}
    - key_url: {{ key_url }}
    {% endif %}
    {% if ppa %}
    - ppa: {{ ppa }}
    {% endif %}
    {% endwith %}
    {% endwith %}
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