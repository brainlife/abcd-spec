#!/bin/bash

for dir in $(ls inputs)
do
  echo "----------- testing $dir"
  (
    cd inputs/$dir
    rm -rf bids
    rm -p output
    ../../../../hooks/bl2bids 
    tree bids > output
    diff expected output > log
    if [[ -s log ]]; 
        then echo "---> ERROR: Test failed."; 
        else echo "---> Test ran successfully."; 
    fi
  )
done
