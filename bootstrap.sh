#!/bin/sh

set -e

ROOTDIR=/opt/clove/deploy

# prepare salt-master configuration and restart salt-master

echo preparing...

# prepare directories

mkdir -p /etc/salt/master.d
mkdir -p $ROOTDIR/{salt,pillar}

# remove master configure file

rm -rf /etc/salt/master.d/clove.conf

# remove states

rm -rf $ROOTDIR/salt/reactor
rm -rf $ROOTDIR/salt/ceph
rm -rf $ROOTDIR/salt/_modules
rm -rf $ROOTDIR/salt/_states

# remove pillars

rm -rf $ROOTDIR/pillar/ceph
rm -rf $ROOTDIR/pillar/top.sls

# copy master configure file

cp $PWD/etc/clove.conf /etc/salt/master.d/

# copy states

cp -r $PWD/reactor/ $ROOTDIR/salt/
cp -r $PWD/ceph/ $ROOTDIR/salt/
cp -r $PWD/_modules/ $ROOTDIR/salt/
cp -r $PWD/_states/ $ROOTDIR/salt/

# copy pillars

cp -r $PWD/examples/pillar/ceph/ $ROOTDIR/pillar/
cp $PWD/examples/pillar/top.sls $ROOTDIR/pillar/

# start salt-master service

if which systemctl > /dev/null 2>&1; then
systemctl enable salt-master
systemctl restart salt-master
else
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



