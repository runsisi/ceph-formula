{% from "ceph/lookup.jinja" import pkg with context %}

ceph.pkg.install:
  pkg.installed:
    - names:
    {% for pkg in pkg.pkgs %}
      - {{ pkg }}
    {% endfor %}

{% if pkg.manage_repo %}
{% for repo in pkg.repos %}
ceph.repo.{{ repo.humanname }}.setup:
  pkgrepo.managed:
{% if salt['grains.get']('os_family') in ['Debian', 'Deepin'] %}
    - name: {{ repo.name }}
    - humanname: {{ repo.humanname }}
    - dist: {{ repo.dist }}
    - file: {{ repo.file }}
    - key_url: {{ repo.key_url }}
{% elif salt['grains.get']('os_family') in ['RedHat'] %}
    - name: {{ repo.name }}
    - humanname: {{ repo.humanname }}
    - baseurl: {{ repo.baseurl }}
    - gpgcheck: {{ repo.gpgcheck }}
    {% if repo.gpgcheck %}
    - gpgkey: {{ repo.gpgkey }}
    {% endif %}
{% endif %}
    - require_in:
      - pkg: ceph.pkg.install
{% endfor %}
{% endif %}