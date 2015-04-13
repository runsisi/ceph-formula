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

BOOTSTRAP=clove/bootstrap.py

trap 'cleanup' EXIT

cleanup() {
    rm -rf $tmpdata
    rm -rf $tmpdir
}

logerror() {
    printf "${RED}[ERROR] ${NORMAL}%s\nExiting now!\n" "$1" 1>&2
    exit 1
}

logwarning() {
    printf "${MAGENTA}[WARN ] ${NORMAL}%s\n" "$1"
}

loginfo() {
    printf "${BLUE}[INFO ] ${NORMAL}%s\n" "$1"
}

logdebug() {
    printf "${BLACK}[DEBUG] ${NORMAL}%s\n" "$1"
}

lower() {
    echo "$1" | sed 'y/ABCDEFGHIJKLMNOPQRSTUVWXYZ/abcdefghijklmnopqrstuvwxyz/'
}

detect_platform() {
    kernel=$(lower $(uname -s))

    if [ $kernel = 'linux' ]; then
        __PLATFORM='linux'
    elif ! case $kernel in cygwin*) false;; esac; then
        __PLATFORM='cygwin'
    elif ! case $kernel in mingw*) false;; esac; then
        __PLATFORM='mingw'
    elif [ $kernel = 'freebsd' ]; then
        __PLATFORM='freebsd'
    else
        __PLATFORM=''
    fi

    readonly __PLATFORM
}

# TODO: more distros
detect_distro() {
    __DISTROFAMILY=''
    __DISTRONAME=''
    __DISTROCODE=''
    __DISTROMAJORVER=''

    if [ -f /etc/redhat-release ]; then
        __DISTROFAMILY='redhat'
        __DISTRONAME=$(cat /etc/redhat-release |sed s/\ release.*//)
        __DISTROCODE=$(cat /etc/redhat-release | sed s/.*\(// | sed s/\)//)
        __DISTROMAJORVER=$(cat /etc/redhat-release | sed s/.*release\ // | sed s/\ .*// | cut -d '.' -f 1)
    elif [ -f /etc/debian_version ] ; then
        __DISTROFAMILY='debian'
        if [ -f /etc/lsb-release ] ; then
            __DISTRONAME=$(cat /etc/lsb-release | grep '^DISTRIB_ID' | awk -F=  '{print $2}')
            __DISTROCODE=$(cat /etc/lsb-release | grep '^DISTRIB_CODENAME' | awk -F=  '{print $2}')
            __DISTROMAJORVER=$(cat /etc/lsb-release | grep '^DISTRIB_RELEASE' | awk -F=  '{print $2}' | cut -d '.' -f 1)
        fi
    fi

    __DISTRONAME=$(lower $__DISTRONAME)
    __DISTROCODE=$(lower $__DISTROCODE)

    if ! case __DISTRONAME in redhat* | 'red hat'*) false;; esac; then
        __DISTRONAME='redhat'
    elif ! case __DISTRONAME in scientific*) false;; esac; then
        __DISTRONAME='scientific'
    elif ! case __DISTRONAME in suse* | opensuse*) false;; esac; then
        __DISTRONAME='suse'
    elif ! case $__DISTRO in centos*) false;; esac; then
        __DISTRO='centos'
    fi

    readonly __DISTROFAMILY
    readonly __DISTRONAME
    readonly __DISTROCODE
    readonly __DISTROMAJORVER
}

query() {
    printf 'Preparing to install clove-deploy:\n'
    printf '   1) I am ready, please go\n'
    printf '   2) Not sure, quit\n'

    until [ x$ans != x ]; do
        read -p 'Your choice: ' ans
        case $ans in
            1)
            ;;
            2)
            exit 1
            ;;
            *)
            ans=
            ;;
        esac
    done
}

detect_platform

if [ $__PLATFORM != 'linux' ]; then
    logerror 'We only support GNU/Linux!'
fi

detect_distro

if [ $__DISTROFAMILY != 'redhat' ]; then
    logerror 'We only support RedHat family!'
fi

query

logdebug 'Unpacking..'

tmpdata=$(mktemp --suffix=.clove)
tail -n +__HDRLINECNT__ $0 > $tmpdata

logdebug 'Done'

if ! which xz > /dev/null 2>&1; then
    logerror 'No xz compression tool found'
fi

if which md5sum > /dev/null 2>&1; then
    logdebug 'Verifying MD5..'

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

loginfo 'Bootstrap..'

if ! python $tmpdir/$BOOTSTRAP $@; then
    logerror 'Bootstrap process failed'
fi

loginfo "Installation has finished, everything's OK!"

exit 0
