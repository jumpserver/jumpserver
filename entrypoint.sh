#!/bin/bash
function cleanup()
{
    local pids=`jobs -p`
    if [[ "$pids" != ""  ]]; then
        kill $pids >/dev/null 2>/dev/null
    fi
}

service="all"
if [ "$1" != "" ];then
    service=$1
fi

trap cleanup EXIT
python jms start $service
