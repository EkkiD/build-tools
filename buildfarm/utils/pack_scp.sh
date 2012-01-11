#!/bin/bash

# $1 : name of the compressed file
# $2 : files to compress
# $3 : username
# $4 : ssh key file
# $5 : target location

tar -czf $1 $2

scp -o User=$3 -o IdentityFile=~/.ssh/$4 $1 $5

rm $1
