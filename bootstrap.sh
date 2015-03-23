#!/bin/sh

set -e

# prepare salt-master configuration and restart salt-master

echo preparing...

mkdir -p /srv/{salt,pillar}
mkdir -p /etc/salt/master.d

rm -rf /srv/salt/reactor
rm -rf /etc/salt/master.d/reactor.conf


rm -rf /srv/salt/ceph
rm -rf /srv/salt/_modules
rm -rf /srv/salt/_states

rm -rf /srv/pillar/ceph
rm -rf /srv/pillar/top.sls


cp -r $PWD/reactor/ /srv/salt/
cp $PWD/etc/reactor.conf /etc/salt/master.d/

cp -r $PWD/ceph/ /srv/salt/
cp -r $PWD/_modules/ /srv/salt/
cp -r $PWD/_states/ /srv/salt/

cp -r $PWD/examples/pillar/ceph/ /srv/pillar/
cp $PWD/examples/pillar/top.sls /srv/pillar/

service salt-master restart

echo
echo OK!

echo
echo NOTE: Define \'/etc/salt/roster\' if you want to use salt-ssh,
echo '      'refer to \'examples/etc/roster\' as an example.

