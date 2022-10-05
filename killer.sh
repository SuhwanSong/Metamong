#!/bin/bash
# This script will kill process which running more than X hours
# egrep: the selected process; grep: hours
while true
do
  PIDS="`ps eaxo etimes,pid,comm | egrep "firefox|chrome|geckodriver" | awk ' { if ($1 > 7200) print $2 }'`"

# Kill the process
  for i in ${PIDS}; do { echo "Killing $i"; kill -15 $i; }; done;
  sleep 60;
done
