#!/bin/bash

# $1 : url where files are located
# $2 : compressed file expected
# $3 - $N : list of files expected in case compressed files doesn't exist

wget -O wget_unpack.tar.gz ${1}/${2}

getResult=$?

tar -xzvf wget_unpack.tar.gz

unpackResult=$?

# if these steps succeed, add ".old" to the suffixes
# if these steps fail, go get the files individually.

if [ $getResult -eq 0 ] && [ $unpackResult -eq 0 ]; then
    echo "Got the packed files"
    for ((i=3 ; i <= $# ; i++ )); do
        echo "mv ./${!i} ./${!i}.old"
        mv ./${!i} ./${!i}.old
    done
else
    echo "Packed file not available, try getting individual files"
    for ((i=3 ; i <= $# ; i++ )); do
        wget -O ${!i}.old ${1}/${!i}
    done
fi
rm wget_unpack.tar.gz
