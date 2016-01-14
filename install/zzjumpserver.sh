#!/bin/bash

export LANG='zh_CN.UTF-8'

if [ "$USER" != "admin" ] && [ "$USER" != "root" ];then
        python /opt/jumpserver/connect.py
        if [ $USER == 'guanghongwei' ];then
            echo
        else
            exit 3
            echo
        fi
fi
