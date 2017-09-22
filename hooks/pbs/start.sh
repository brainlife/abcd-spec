#!/bin/bash

echo "starting $1 on $HOSTNAME"

[ ! $SERVICE_DIR ] && SERVICE_DIR=$PWD

resource="-l nodes=1"
[ $CPUS ] && resource=$resource:"ppn=$CPUS"
[ $WALLTIME ] && resource=$resource:"walltime=$WALLTIMME"
cmd="qsub $resource -d $PWD $SERVICE_DIR/$1"
echo $cmd
jobid=`$cmd`
echo $jobid > jobid
