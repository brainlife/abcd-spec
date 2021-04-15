#!/bin/bash

set -e

for dir in $(ls inputs)
#for dir in simple
do

  echo
  echo --------------------------
  echo $dir
  echo --------------------------
  echo

  (
    cd inputs/$dir
    rm -rf bids
    rm -f output
    ../../../../hooks/bl2bids 
    tree bids | tee output
    diff expected output | tee log
    if [[ -s log ]]; 
        then echo "---> ERROR: Test failed." >&1 && exit 1
        else echo "---> Test ran successfully."; 
    fi
  )
done

echo "all test ran successfully"
