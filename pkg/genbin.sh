#!/bin/sh

# runsisi AT hust.edu.cn

set -e

CWD=$(cd -P $(dirname $0) && pwd -P)

. $CWD/util.sh

BIN_SUFFIX='.bin'

trap 'cleanup' EXIT

cleanup() {
    rm -rf $tmphdr
}

usage() {
    printf "Usage:\n"
    printf "   $(basename $0) [-h /path/to/header] [-o /path/to/output] /path/to/data\n\n"
    printf "Notes:\n"
    printf "   Data must be a regular file\n"

    exit 1
}

while getopts 'h:o:' opt; do
    case $opt in
        h)
        hdr=$OPTARG
        ;;
        o)
        out=$OPTARG
        ;;
        ?)
        usage
        ;;
    esac
done

shift $((OPTIND - 1))

if [ $# -ne 1 ]; then
    usage
fi

data=$1

if [ ! -f $data ]; then
    logerror 'Not a regular file or not exist'
fi

if [ x$hdr = x ]; then
    hdr=$CWD/binhdr.sh
fi

if [ ! -f $hdr ]; then
    logerror 'Bin header file not exist'
fi

if ! grep __CSUM__ $hdr > /dev/null 2>&1 \
    || ! grep __HDRLINECNT__ $hdr > /dev/null 2>&1; then
    logerror 'Bin header apears to be broken'
fi

dir=$(dirname $data)
base=$(basename $data | cut -d '.' -f 1)

if [ x$out = x ]; then
    out=$dir/$base$BIN_SUFFIX
else
    dir=$(dirname $out)
    base=$(basename $out)
    mkdir -p $dir
    out=$dir/$base
    if [ -d $out ]; then
        logerror 'Output path is an existing directory'
    fi
fi

linecnt=$(($(wc -l $hdr | awk '{print $1}') + 1))
tmphdr=$(mktemp)

if which md5sum > /dev/null 2>&1; then
    csum=$(md5sum -b $data | awk '{print $1}')
    cat $hdr | sed -e s/__CSUM__/$csum/ -e s/__HDRLINECNT__/$linecnt/ > $tmphdr
else
    cat $hdr | sed -e s/__HDRLINECNT__/$linecnt/ > $tmphdr
fi

cat $tmphdr $data > $out
chmod +x $out
