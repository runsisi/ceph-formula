{% if grains['os_family'] in ['Debian',] %}
ceph.repo.cleanup.1:
  file.managed:
    - name: /etc/apt/sources.list
    - contents: ' '
ceph.repo.cleanup.2:
  file.directory:
    - name: /etc/apt/sources.list.d
    - clean: True
{% elif grains['os_family'] in ['RedHat'] %}
ceph.repo.cleanup:
  file.directory:
    - name: /etc/yum.repos.d
    - clean: True
{% endif %}
