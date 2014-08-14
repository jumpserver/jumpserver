#!/bin/bash

if [ $USER = 'yolu' ] || [ $USER == 'root' ];then
    echo ""
else
    python /opt/jumpserver/jumpserver.pyo
    if [ $USER == 'guanghongwei' ] || [ $USER  == 'liufuhua' ];then
        echo
    else
        exit 3
        echo
    fi
fi