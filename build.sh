#!/bin/bash
#

version=$1
if [ -z "$version" ];then
    echo "Usage: sh build version"
    exit
fi


docker build -t jumpserver/jumpserver:$version .
