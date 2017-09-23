#!/bin/bash

echo "starting $1 on $HOSTNAME"

[ ! $SERVICE_DIR ] && SERVICE_DIR=$PWD

resource="-l nodes=1"
while getopts ":s:c:t:" opt; do
    case "$opt" in
    s) 	script=$OPTARG
        ;;
    c) 	resource=$resource:"ppn=$OPTARG"
        ;;
    t)  resource=$resource:"walltime=$OPTARG"
        ;;
    esac
done

cmd="qsub $resource -d $PWD $SERVICE_DIR/$script"
echo $cmd
jobid=`$cmd`
echo $jobid > jobid
