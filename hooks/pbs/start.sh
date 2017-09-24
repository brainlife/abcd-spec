#!/bin/bash

[ ! $SERVICE_DIR ] && SERVICE_DIR=$PWD

resource="-l nodes=1"
while getopts ":s:c:t:" opt; do
    case "$opt" in
    s) 	script=$OPTARG
        ;;
    c) 	resource="$resource:ppn=$OPTARG"
        ;;
    t)  resource="$resource -l walltime=$OPTARG"
        ;;
    esac
done

echo "qsub on $HOSTNAME"
echo "  $resource"
echo "  -d $PWD -V -o \$PBS_JOBID.log -e \$PBS_JOBID.error.log"
echo "  $SERVICE_DIR/$script"

#needs to be the last command to return exit code
qsub $resource -d $PWD -V -o \$PBS_JOBID.log -e \$PBS_JOBID.error.log $SERVICE_DIR/$script > jobid
