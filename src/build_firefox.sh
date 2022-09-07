#! /bin/bash
# ref: https://gitlab.com/noencoding/OS-X-Chromium-with-proprietary-codecs/-/wikis/List-of-all-gn-arguments-for-Chromium-build
# set -o xtrace

CUR_DIR="$( cd "$(dirname "$0")" ; pwd -P )"/..
CHM_DIR=$CUR_DIR/firefox/mozilla-central

GIT_VER=$1

pushd $CHM_DIR &> /dev/null
hg update $GIT_VER
#./mach clobber

if [ "$2" = "no" ]; then
  popd &> /dev/null
  exit 0
fi
./mach build

mv obj-x86_64-pc-linux-gnu/ ../$GIT_VER
ln -s ../$GIT_VER/dist/bin/firefox ../$GIT_VER/firefox 

popd &> /dev/null
echo $PWD

