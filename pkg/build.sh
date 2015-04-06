#!/bin/sh

# runsisi AT hust.edu.cn

set -e

CWD=$(cd -P $(dirname $0) && pwd -P)

. $CWD/util.sh

trap 'cleanup' EXIT

cleanup() {
    rm -rf $tmpdir
    rm -rf $tmpxz
    rm -rf $tmpbin
}

usage() {
    printf "Usage:\n"
    printf "   $(basename $0) [-o /path/to/output]\n\n"

    exit 1
}

while getopts 'o:' opt; do
    case $opt in
        o)
        out=$OPTARG
        ;;
        ?)
        usage
        ;;
    esac
done

shift $((OPTIND - 1))

if [ $# -ne 0 ]; then
    usage
fi

dir=$CWD
if [ x$out = x ]; then
    out=$dir/clove.bin
else
    dir=$(dirname $out)
    mkdir -p $dir
    if [ -d $out ]; then
        logerror 'Output path is an existing directory'
    fi
fi

# create a .xz compressed fileC

if ! which xz > /dev/null 2>&1; then
    logerror 'No xz compression tool found'
fi

# collect clove

tmpdir=$(mktemp --directory --suffix=.clove)

cp -rf $CWD/clove   $tmpdir

# collect ceph-formula

formula_dir=$tmpdir/clove/ceph-formula
mkdir -p $formula_dir

cp -rf $CWD/../_modules     $formula_dir
cp -rf $CWD/../_states      $formula_dir
cp -rf $CWD/../ceph         $formula_dir
cp -rf $CWD/../etc          $formula_dir
cp -rf $CWD/../examples     $formula_dir
cp -rf $CWD/../reactor      $formula_dir
cp -ff $CWD/../install.sh   $formula_dir

tmpxz=$(mktemp --suffix=.clove)

loginfo 'Create .xz compressed file'
cd $tmpdir
if ! tar -cJf $tmpxz clove/ > /dev/null; then
    logerror 'Failed to compress'
fi

# build bin

tmpbin=$(mktemp --suffix=.clove)

loginfo 'Generate bin'
if ! sh $CWD/genbin.sh -o $tmpbin $tmpxz; then
    error 'Failed to generate'
fi

loginfo "Output to dir $out"
mv $tmpbin $out

loginfo 'success!'