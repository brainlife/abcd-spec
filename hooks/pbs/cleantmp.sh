#!/bin/bash
JOBID=$1
USERID=$2
GROUPID=$3
JOBNAME=$4
SESSION=$5
#$6 = resource list 
#$7 = resource used 
#$8 = queue name 
#$9 = account string

echo "epilogue/cleantmp.sh: removing /tmp/$JOBID"
sleep 10 #give singularity/cleanupd to do some work (before getting killed by wall)
rm -rf /tmp/$JOBID
