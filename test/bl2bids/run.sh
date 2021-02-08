#!/bin/bash

for dir in $(ls inputs)
do
  echo "----------- testing $dir"
  (
    cd inputs/$dir
    ../../../../hooks/bl2bids 
    tree bids > output
    diff expected output
  )
done
