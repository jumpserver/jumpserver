#!/bin/bash
function cleanup()
{
    local pids=`jobs -p`
    if [[ "${pids}" != ""  ]]; then
        kill ${pids} >/dev/null 2>/dev/null
    fi
}

service="all"
if [[ "$1" != "" ]];then
    service=$1
fi

trap cleanup EXIT
if [[ "$1" == "bash" ]];then
    bash
else
    python jms start ${service}
fi

