#!/bin/bash

echo "starting $1 on $HOSTNAME"
jobid=`qsub -d $PWD $SERVICE_DIR/$1`
echo $jobid > jobid
