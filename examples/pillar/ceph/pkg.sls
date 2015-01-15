{% if salt['grains.get']('os_family') in ['Debian', 'Deepin'] %}
ceph:
  pkg:
    pkgs:
      - ceph
    manage_repo: True
    repos:
      - name: deb http://ceph.com/debian-giant {{ salt['grains.get']('oscodename') }} main
        humanname: ceph
        dist: {{ salt['grains.get']('oscodename') }}
        file: /etc/apt/sources.list.d/ceph.list
        key_url: https://ceph.com/git/?p=ceph.git;a=blob_plain;f=keys/release.asc
{% elif salt['grains.get']('os_family') in ['RedHat'] %}
ceph:
  pkg:
    pkgs:
      - ceph
    manage_repo: True
    repos:
      - name: ceph
        humanname: ceph
        baseurl: http://ceph.com/rpm-giant/el{{ salt['grains.get']('osmajorrelease')[0] }}/$basearch
        gpgcheck: 1
        gpgkey: https://ceph.com/git/?p=ceph.git;a=blob_plain;f=keys/release.asc

      - name: base
        humanname: base
        baseurl: http://mirrors.ustc.edu.cn/centos/{{ salt['grains.get']('osmajorrelease')[0] }}/os/$basearch
        gpgcheck: 1
        gpgkey: http://mirrors.ustc.edu.cn/centos/RPM-GPG-KEY-CentOS-{{ salt['grains.get']('osmajorrelease')[0] }}

      - name: extras
        humanname: extras
        baseurl: http://mirrors.ustc.edu.cn/centos/{{ salt['grains.get']('osmajorrelease')[0] }}/extras/$basearch
        gpgcheck: 1
        gpgkey: http://mirrors.ustc.edu.cn/centos/RPM-GPG-KEY-CentOS-{{ salt['grains.get']('osmajorrelease')[0] }}

      - name: epel
        humanname: epel
        baseurl: http://mirrors.ustc.edu.cn/epel/{{ salt['grains.get']('osmajorrelease')[0] }}/$basearch
        gpgcheck: 1
        gpgkey: http://mirrors.ustc.edu.cn/epel/RPM-GPG-KEY-EPEL-{{ salt['grains.get']('osmajorrelease')[0] }}
{% endif %}