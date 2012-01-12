#!/bin/bash

# $1 : name of the compressed file
# $2 : directory to move to
# $3 : files to compress
# $4 : username
# $5 : ssh key file
# $6 : target location

echo "tar -cz -C ${2} -f ${1} ${3}"
tar -cz -C $2 -f $1 $3

echo "scp -o User=$4 -o IdentityFile=~/.ssh/$5 $1 $6"
scp -o User=$4 -o IdentityFile=~/.ssh/$5 $1 $6

rm $1
