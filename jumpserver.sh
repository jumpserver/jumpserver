#!/bin/bash

if [ $USER = 'admin' ] || [ $USER == 'root' ];then
    echo ""
else
    python /opt/jumpserver/jumpserver.pyo
    if [ $USER == 'guanghongwei' ];then
        echo
    else
        exit 3
        echo
    fi
fi