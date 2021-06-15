#!/bin/bash

#make sure subject name is cleaned on both json and bids filepath
subject=$(jq -r .subject bids/sub-sub11061/anat/sub-sub11061_T1w.json)
if [ $subject != "sub11061" ]; then
    echo "bad subject $subject"
    exit 1
fi

echo "check.sh all good"
