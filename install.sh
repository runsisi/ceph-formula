#!/bin/sh

# runsisi AT hust.edu.cn

#!/bin/sh

set -e

CWD=$(cd -P $(dirname $0) && pwd -P)
SALTDIR=/opt/clove_deploy
PILLARDIR=/etc/clove_deploy

# prepare directories

mkdir -p $SALTDIR
mkdir -p $PILLARDIR
mkdir -p /etc/salt/master.d

# remove examples

rm -rf /etc/clove_deploy/examples

# remove master configure file

rm -rf /etc/salt/master.d/clove.conf

# remove states, modules etc.

rm -rf $SALTDIR/*

# backup pillars

if [ ! -f $PILLARDIR/clove.sls.bak -a -f $PILLARDIR/clove.sls ]; then
    mv -f $PILLARDIR/{clove.sls,clove.sls.bak}
fi

# copy examples

cp -r $CWD/examples/ /etc/clove_deploy/

# copy master configure file

cp $CWD/etc/clove.conf /etc/salt/master.d/

# copy states, modules etc.

cp -r $CWD/reactor/ $SALTDIR
cp -r $CWD/ceph/ $SALTDIR
cp -r $CWD/_modules/ $SALTDIR
cp -r $CWD/_states/ $SALTDIR

# copy pillars

cp -r $CWD/examples/pillar/clove.sls $PILLARDIR
cp -f $CWD/examples/pillar/top.sls $PILLARDIR
