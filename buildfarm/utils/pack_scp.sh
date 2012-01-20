#!/bin/bash

# $1 : name of the compressed file
# $2 : directory to move to
# $3 : files to compress
# $4 : username
# $5 : ssh key file
# $6 : target location
set -e

pushd `dirname $0` &> /dev/null
MY_DIR=$(pwd)
popd &> /dev/null
retry="$MY_DIR/retry.py -s 1 -r 2"

usage()
{
    echo "Usage: pack_scp.sh COMP_FILE DIR FILES USERNAME SSH_KEY TARGET"
    echo  "        COMP_FILE: name of compressed file"
    echo  "        DIR:       directory to move to before compression"
    echo  "        FILES:     files to compress"
    echo  "        USERNAME:  ssh username"
    echo  "        SSH_KEY:   ssh key file"
    echo  "        TARGET:    Target location"
}

# if incorrect number of args
if [ $# -ne 6 ] ; then
    usage
    exit 1
fi

#if directory does not exist
if [ ! -d ${2} ] ; then
    echo "Error: Directory to compress from not found."
    usage
    exit 1
fi

# if ssh key does not exist
if [ ! -f "${HOME}/.ssh/${5}" ] ; then
    echo "Error: SSH key file does not exist"
    usage
    exit 1
fi


echo "tar -cz -C ${2} -f ${1} ${3}"
tar -cz -C $2 -f $1 $3

echo "${retry} scp -o User=$4 -o IdentityFile=~/.ssh/$5 $1 $6"
${retry} scp -o User=$4 -o IdentityFile="~/.ssh/$5" $1 $6

rm $1
