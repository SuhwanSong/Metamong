#! /bin/bash
# ref: https://gitlab.com/noencoding/OS-X-Chromium-with-proprietary-codecs/-/wikis/List-of-all-gn-arguments-for-Chromium-build
# set -o xtrace

CUR_DIR="$( cd "$(dirname "$0")" ; pwd -P )"/../../
CHM_DIR=$CUR_DIR/firefox/mozilla-central

GIT_VER=$1

CONFIG_DIR=$CHM_DIR/outputs/$GIT_VER

pushd $CHM_DIR &> /dev/null
rm -rf $CONFIG_DIR
mkdir $CONFIG_DIR

echo "mk_add_options MOZ_OBJDIR=@TOPSRCDIR@/outputs/$GIT_VER" >> $CONFIG_DIR/mozconfig 
echo 'ac_add_options --enable-release' >> $CONFIG_DIR/mozconfig


hg update $GIT_VER --clean
./mach clobber
echo -ne '1\nn' | ./mach bootstrap
MOZCONFIG=$CONFIG_DIR/mozconfig ./mach build
retVal=$?
if [ $retVal -ne 0 ]; then
    exit 1
fi
mkdir ../$GIT_VER
ln -s $CONFIG_DIR/dist/bin/firefox ../$GIT_VER/firefox 
ln -s ../geckodriver ../$GIT_VER/geckodriver
popd &> /dev/null
echo $PWD
exit 0
