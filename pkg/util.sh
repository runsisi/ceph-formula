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

