#!/bin/sh

# runsisi AT hust.edu.cn

#!/bin/sh

set -e

CWD=$(cd -P $(dirname $0) && pwd -P)
ROOTDIR=/opt/clove/deploy

# prepare directories

mkdir -p /etc/salt/master.d
mkdir -p /etc/clove/deploy
mkdir -p $ROOTDIR/{salt,pillar}

# remove examples

rm -rf /etc/clove/examples

# remove master configure file

rm -rf /etc/salt/master.d/clove.conf

# remove states

rm -rf $ROOTDIR/salt/reactor
rm -rf $ROOTDIR/salt/ceph
rm -rf $ROOTDIR/salt/_modules
rm -rf $ROOTDIR/salt/_states

# backup pillars

if [ -d /etc/clove/deploy/ceph ]; then
    mv -f /etc/clove/deploy/ceph /etc/clove/deploy/ceph.bak
fi

# copy examples

cp -r $CWD/examples/ /etc/clove/

# copy master configure file

cp $CWD/etc/clove.conf /etc/salt/master.d/

# copy states

cp -r $CWD/reactor/ $ROOTDIR/salt/
cp -r $CWD/ceph/ $ROOTDIR/salt/
cp -r $CWD/_modules/ $ROOTDIR/salt/
cp -r $CWD/_states/ $ROOTDIR/salt/

# copy pillars

cp -r $CWD/examples/pillar/ceph/ /etc/clove/deploy/
cp -f $CWD/examples/pillar/top.sls /etc/clove/deploy/
