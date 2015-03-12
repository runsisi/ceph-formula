{% if grains['os_family'] in ['Debian',] %}
ceph:
  bootstrap:
    repo:
      cleanup: 0
      repos:
        - name: deb http://10.118.202.154/ubuntu {{ grains['oscodename'] }} main restricted universe multiverse
          humanname: base
          dist: {{ grains['oscodename'] }}
          file: /etc/apt/sources.list

        - name: deb http://10.118.202.154/ubuntu {{ grains['oscodename'] }}-updates main restricted universe multiverse
          humanname: updates
          dist: {{ grains['oscodename'] }}-updates
          file: /etc/apt/sources.list

        - name: deb http://10.118.202.154/ubuntu {{ grains['oscodename'] }}-security main restricted universe multiverse
          humanname: security
          dist: {{ grains['oscodename'] }}-security
          file: /etc/apt/sources.list

        - name: salt
          humanname: salt
          dist: {{ grains['oscodename'] }}
          file: /etc/apt/sources.list.d/saltstack-salt.list
          ppa: saltstack/salt
{% elif grains['os_family'] in ['RedHat'] %}
ceph:
  bootstrap:
    repo:
      cleanup: 1
      repos:
        - name: base
          humanname: base
          baseurl: http://10.118.202.154/centos/{{ grains['osmajorrelease'] }}/os/$basearch
          gpgcheck: 1
          gpgkey: http://10.118.202.154/centos/RPM-GPG-KEY-CentOS-{{ grains['osmajorrelease'] }}

        - name: extras
          humanname: extras
          baseurl: http://10.118.202.154/centos/{{ grains['osmajorrelease'] }}/extras/$basearch
          gpgcheck: 1
          gpgkey: http://10.118.202.154/centos/RPM-GPG-KEY-CentOS-{{ grains['osmajorrelease'] }}

        - name: updates
          humanname: updates
          baseurl: http://10.118.202.154/centos/{{ grains['osmajorrelease'] }}/updates/$basearch
          gpgcheck: 1
          gpgkey: http://10.118.202.154/centos/RPM-GPG-KEY-CentOS-{{ grains['osmajorrelease'] }}

        - name: epel
          humanname: epel
          baseurl: http://10.118.202.154/epel/{{ grains['osmajorrelease'] }}/$basearch
          gpgcheck: 1
          gpgkey: http://10.118.202.154/epel/RPM-GPG-KEY-EPEL-{{ grains['osmajorrelease'] }}
{% endif %}
