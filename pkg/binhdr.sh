#!/bin/sh

# runsisi AT hust.edu.cn

set -e

# http://stackoverflow.com/questions/4332478/read-the-current-text-
# color-in-a-xterm/4332530#4332530
BLACK=$(tput setaf 0)
RED=$(tput setaf 1)
GREEN=$(tput setaf 2)
YELLOW=$(tput setaf 3)
LIME_YELLOW=$(tput setaf 190)
POWDER_BLUE=$(tput setaf 153)
BLUE=$(tput setaf 4)
MAGENTA=$(tput setaf 5)
CYAN=$(tput setaf 6)
WHITE=$(tput setaf 7)
BRIGHT=$(tput bold)
NORMAL=$(tput sgr0)
BLINK=$(tput blink)
REVERSE=$(tput smso)
UNDERLINE=$(tput smul)

BOOTSTRAP=clove/bootstrap/bootstrap.py

trap 'cleanup' EXIT

cleanup() {
    rm -rf $tmpdata
    rm -rf $tmpdir
}

logerror() {
    msg=$1
    printf "${RED}[ERROR] ${NORMAL}%s\nExiting now!\n" "$msg" 1>&2
    exit 1
}

logwarning() {
    msg=$1
    printf "${MAGENTA}[WARN ] ${NORMAL}%s\n" "$msg"
}

loginfo() {
    msg=$1
    printf "${BLUE}[INFO ] ${NORMAL}%s\n" "$msg"
}

logdebug() {
    msg=$1
    printf "${BLACK}[DEBUG] ${NORMAL}%s\n" "$msg"
}

query() {
    printf 'Preparing to install clove_deploy:\n'
    printf '   1) I am ready, please go\n'
    printf '   2) Not sure, quit\n'

    until [ x$ans != x ]; do
        read -p 'Your choice: ' ans
        case $ans in
            1)
            ;;
            2)
            exit -1
            ;;
            *)
            ans=
            ;;
        esac
    done
}

query

logdebug 'Unpacking...'

tmpdata=$(mktemp --suffix=.clove)
tail -n +__HDRLINECNT__ $0 > $tmpdata

logdebug 'Done'

if ! which xz > /dev/null 2>&1; then
    logerror 'No xz compression tool found'
fi

if which md5sum > /dev/null 2>&1; then
    logdebug 'Verifying MD5...'

    csum=$(md5sum -b $tmpdata | awk '{print $1}')
    if [ $csum != __CSUM__ ]; then
        logerror 'Package appears to be corrupted'
    fi

    logdebug 'Done'
fi

# bootstrap
tmpdir=$(mktemp --directory --suffix=.clove)
if ! tar -xJf $tmpdata -C $tmpdir > /dev/null 2>&1; then
    logerror 'Not an .xz package?'
fi

if [ ! -f $tmpdir/$BOOTSTRAP ];  then
    logerror "$BOOTSTRAP does not exist in package"
fi

loginfo 'Bootstrap...'
if ! python $tmpdir/$BOOTSTRAP $@; then
    logerror 'Bootstrap process failed'
fi

loginfo "Installation has finished, everything's OK!"

printf '
1) Define "/etc/salt/roster" if you want to use salt-ssh, refer
   to "/etc/clove/examples/etc/roster" as an example.
2) Please modify pillar data under "/opt/clove/deploy/pillar/ceph/"
   to fit your need.\n
'

exit 0
