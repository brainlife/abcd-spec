#!/bin/bash

#for dir in $(ls inputs)
for dir in multi
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
        then echo "---> ERROR: Test failed."; 
        else echo "---> Test ran successfully."; 
    fi
  )
done
