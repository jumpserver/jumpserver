#!/bin/bash
# Date: 2015-04-12
# Version: 2.0.0
# Site: http://www.jumpserver.org
# Author: jumpserver group

. /etc/init.d/functions

base_dir=$(dirname $0)

case $1 in
start)
    python $base_dir/manage.py runserver 0.0.0.0:80 &
    python $base_dir/log_handler.py &
    cd $base_dir/websocket/; node index.js &
    ;;

stop)
    pkill -15 runserver
    pkill -15 log_handler.py
    pkill -15 node
    ;;

esac
