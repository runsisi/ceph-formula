#!/bin/sh

# runsisi AT hust.edu.cn

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

lower() {
    echo "$1" | sed 'y/ABCDEFGHIJKLMNOPQRSTUVWXYZ/abcdefghijklmnopqrstuvwxyz/'
}

uuper() {
    echo "$1" | sed 'y/abcdefghijklmnopqrstuvwxyz/ABCDEFGHIJKLMNOPQRSTUVWXYZ/'
}

# $OSTYPE only exist in bash, and [[ ]] is not supported under dash
#detect_platform() {
#    if [[ "$OSTYPE" == "linux-gnu" ]]; then
#        __PLTTFORM='linux'
#    elif [[ "$OSTYPE" == "darwin"* ]]; then
#        __PLATFORM='mac'
#    elif [[ "$OSTYPE" == "cygwin" ]]; then
#        __PLATFORM='cygwin'
#    elif [[ "$OSTYPE" == "msys" ]]; then
#        __PLATFORM='msys'
#    elif [[ "$OSTYPE" == "win32" ]]; then
#        __PLATFORM='windows'
#    elif [[ "$OSTYPE" == "freebsd"* ]]; then
#        __PLATFORM='freebsd'
#    else
#        __PLATFORM=''
#    fi
#    readonly __PLATFORM
#}

detect_platform() {
    kernel=$(lower $(uname -s))

    if [ $kernel = 'linux' ]; then
        __PLATFORM='linux'
    elif ! case $kernel in cygwin*) false;; esac; then
        __PLATFORM='cygwin'
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
    elif ! case $__DISTRO in cenos*) false;; esac; then
        __DISTRO='centos'
    fi

    readonly __DISTROFAMILY
    readonly __DISTRONAME
    readonly __DISTROCODE
    readonly __DISTROMAJORVER
}
