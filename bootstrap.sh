#!/bin/sh

set -e

CWD=$(cd -P $(dirname $0) && pwd -P)
cd $CWD

ROOTDIR=/opt/clove/deploy

# prepare salt-master configuration

echo preparing...

if ! which salt-master > /dev/null 2>&1; then
    echo salt-master not installed
    exit 1
fi

if ! which salt-ssh > /dev/null 2>&1; then
    echo salt-ssh not installed
    exit 1
fi

/bin/sh install.sh

# start salt-master service

if which systemctl > /dev/null 2>&1; then
    systemctl disable firewalld
    systemctl stop firewalld
    systemctl enable salt-master
    systemctl restart salt-master
else
    chkconfig iptables off
    service iptables stop
    chkconfig salt-master on
    service salt-master restart
fi

echo
echo OK!

printf '
1) Define "/etc/salt/roster" if you want to use salt-ssh, refer
   to "examples/etc/roster" as an example.
2) Please modify pillar data under "%s"
   to fit your need.\n
' $ROOTDIR/pillar/ceph/



