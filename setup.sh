#! /bin/bash
set -o xtrace

CUR_DIR="$( cd "$(dirname "$0")" ; pwd -P )"
SRC_DIR=$CUR_DIR/src/
TOL_DIR=$CUR_DIR/tools/
DAT_DIR=$CUR_DIR/data

# make directories
mkdir -p $CUR_DIR/firefox
mkdir -p $CUR_DIR/chrome
mkdir -p $TOL_DIR

# install dep
pip3 install imagehash
pip3 install selenium
pip3 install pillow
pip3 install beautifulsoup4
pip3 install lxml
pip3 install requests
pip3 install PyVirtualDisplay
pip3 install deepdiff
pip3 install psutil
pip3 install numpy


# Determine the archive to use. For now, only Mac64 and Linux64 are supported.
archive=$([ "$(uname)" == "Darwin" ] && echo "mac64" || echo "linux64")

# download versions
pushd $DAT_DIR
python3 bisect-builds.py -a $archive --use-local-cache
popd

