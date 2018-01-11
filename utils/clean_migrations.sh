#!/bin/bash
#

cd ../apps

for d in $(ls);do
    if [ -d $d ] && [ -d $d/migrations ];then
        rm -f $d/migrations/00*
    fi
done

