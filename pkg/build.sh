#!/bin/sh

# runsisi AT hust.edu.cn

set -e

CWD=$(cd -P $(dirname $0) && pwd -P)

. $CWD/util.sh

trap 'cleanup' EXIT

cleanup() {
    rm -rf $tmpdir
    rm -rf $tmpgz
    rm -rf $tmpbin
}

usage() {
    printf "Usage:\n"
    printf "   $(basename $0) [-d distro] [-o /path/to/output]\n\n"

    exit 1
}

while getopts 'o:' opt; do
    case $opt in
        o)
        outdir=$OPTARG
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

if [ x$outdir = x ]; then
    outdir=$CWD
else

    if [ -f $outdir ]; then
        logerror 'Output path is an existing file'
    fi
    mkdir -p $outdir
fi

out=$outdir/clove-deploy-$(date +%Y-%m-%d).bin

# create a gzip compressed fileC

if ! which gzip > /dev/null 2>&1; then
    logerror 'No gzip compression tool found'
fi

# collect clove

tmpdir=$(mktemp --directory --suffix=.clove)

cp -rf $CWD/clove $tmpdir

# collect packages

cp -rf $CWD/pkgs-* $tmpdir/clove/

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

tmpgz=$(mktemp --suffix=.clove)

loginfo 'Create gzip compressed file'
cd $tmpdir
if ! tar -czf $tmpgz clove/ > /dev/null; then
    logerror 'Failed to compress'
fi

# build bin

tmpbin=$(mktemp --suffix=.clove)

loginfo 'Generate bin'
if ! sh $CWD/genbin.sh -o $tmpbin $tmpgz; then
    error 'Failed to generate'
fi

loginfo "Output to $out"
mv $tmpbin $out

loginfo 'success!'
