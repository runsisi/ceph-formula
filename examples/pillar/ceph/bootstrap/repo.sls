{% if salt['grains.get']('os_family') in ['Debian',] %}
ceph:
  bootstrap:
    repo:
      cleanup: 0
      repos:
        - name: deb http://mirrors.ustc.edu.cn/ubuntu {{ grains['oscodename'] }} main restricted universe multiverse
          humanname: base
          dist: {{ grains['oscodename'] }}
          file: /etc/apt/sources.list
  
        - name: deb http://mirrors.ustc.edu.cn/ubuntu {{ grains['oscodename'] }}-updates main restricted universe multiverse
          humanname: updates
          dist: {{ grains['oscodename'] }}-updates
          file: /etc/apt/sources.list
  
        - name: deb http://mirrors.ustc.edu.cn/ubuntu {{ grains['oscodename'] }}-security main restricted universe multiverse
          humanname: security
          dist: {{ grains['oscodename'] }}-security
          file: /etc/apt/sources.list
  
        - name: salt
          humanname: salt
          dist: {{ grains['oscodename'] }}
          file: /etc/apt/sources.list.d/saltstack-salt.list
          ppa: saltstack/salt
{% elif salt['grains.get']('os_family') in ['RedHat'] %}
ceph:
  bootstrap:
    repo:
      cleanup: 0
      repos:
        - name: base
          humanname: base
          baseurl: http://mirrors.ustc.edu.cn/centos/{{ grains['osmajorrelease'] }}/os/$basearch
          gpgcheck: 1
          gpgkey: http://mirrors.ustc.edu.cn/centos/RPM-GPG-KEY-CentOS-{{ grains['osmajorrelease'] }}
  
        - name: extras
          humanname: extras
          baseurl: http://mirrors.ustc.edu.cn/centos/{{ grains['osmajorrelease'] }}/extras/$basearch
          gpgcheck: 1
          gpgkey: http://mirrors.ustc.edu.cn/centos/RPM-GPG-KEY-CentOS-{{ grains['osmajorrelease'] }}
  
        - name: epel
          humanname: epel
          baseurl: http://mirrors.ustc.edu.cn/epel/{{ grains['osmajorrelease'] }}/$basearch
          gpgcheck: 1
          gpgkey: http://mirrors.ustc.edu.cn/epel/RPM-GPG-KEY-EPEL-{{ grains['osmajorrelease'] }}
{% endif %}