#!/bin/bash
ulimit
ulimit -n 131072
ulimit -a

BROWSER="chrome"
BROWSER=$1

INPUT_DIR=$2

cp js/metamor.js /tmp 
mkdir -p "internal_eval"

for n in {1..2}
do
  for i in {0..8}
  do
    pkill Xvfb
    pkill chrome
    pkill firefox
    rm -rf /tmp/rust_mozprofile* /tmp/Temp-*
    rm -rf /tmp/.org.chromium.Chromium.*
    OUTPUT="internal_eval"/"$i"_"$BROWSER"_"$n"
    if [ "$BROWSER" = "chrome" ]; then
        SEED="$n" MUTATION="$i" python3 -u metamong.py -i $INPUT_DIR -o "$OUTPUT" --nomin -j 24 -p 106 -n 109 &> "$OUTPUT".txt
    else
        SEED="$n" MUTATION="$i" python3 -u metamong.py -i $INPUT_DIR -o "$OUTPUT" -t firefox --nomin -j 24 -p 106 -n 108 &> "$OUTPUT".txt
    fi
  done
done
