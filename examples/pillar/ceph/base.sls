{% if salt['grains.get']('os_family') in ['Debian', 'Deepin'] %}
ceph:
  base:
    pkgs:
      ceph: 0.87-1{{ grains['oscodename'] }}
    manage_repo: 1
    repos:
      - name: deb http://ceph.com/debian-giant {{ salt['grains.get']('oscodename') }} main
        humanname: ceph
        dist: {{ salt['grains.get']('oscodename') }}
        file: /etc/apt/sources.list.d/ceph.list
        key_url: https://ceph.com/git/?p=ceph.git;a=blob_plain;f=keys/release.asc
{% elif salt['grains.get']('os_family') in ['RedHat'] %}
ceph:
  base:
    pkgs:
      ceph: 0.87-0.el{{ grains['osmajorrelease'] }}
    manage_repo: 1
    repos:
      - name: ceph
        humanname: ceph
        baseurl: http://ceph.com/rpm-giant/el{{ grains['osmajorrelease'] }}/$basearch
        gpgcheck: 1
        gpgkey: https://ceph.com/git/?p=ceph.git;a=blob_plain;f=keys/release.asc

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