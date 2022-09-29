#! /bin/bash
# ref: https://gitlab.com/noencoding/OS-X-Chromium-with-proprietary-codecs/-/wikis/List-of-all-gn-arguments-for-Chromium-build
# set -o xtrace

CUR_DIR="$( cd "$(dirname "$0")" ; pwd -P )"/..
CHM_DIR=$CUR_DIR/firefox/mozilla-central

GIT_VER=$1

pushd $CHM_DIR &> /dev/null
hg update $GIT_VER --clean
./mach clobber
echo -ne '2\nn' | ./mach bootstrap
./mach build
retVal=$?
if [ $retVal -ne 0 ]; then
    echo "Error"
    rm -rf obj-x86_64-pc-linux-gnu/
    exit 1
fi

pushd obj-x86_64-pc-linux-gnu/dist/bin
find . -type l -exec $CUR_DIR/tools/sym_to_real.sh {} +
popd


mv obj-x86_64-pc-linux-gnu/dist/bin ../$GIT_VER
#ln -s ../$GIT_VER/firefox ../$GIT_VER/firefox 
#ln -s ../geckodriver ../$GIT_VER/geckodriver

popd &> /dev/null
echo $PWD
exit 0
