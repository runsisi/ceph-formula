#! /bin/sh

set -x
set -e

echo "192.168.133.9     master.test"    >> /etc/hosts
echo "192.168.133.10    ceph-mon0.test" >> /etc/hosts
echo "192.168.133.100   ceph-osd0.test" >> /etc/hosts

sed -i '/127.0.1.1/d'   /etc/hosts
systemctl stop firewalld
