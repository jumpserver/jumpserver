#!/bin/bash
function cleanup()
{
    local pids=`jobs -p`
    if [[ "$pids" != ""  ]]; then
        kill $pids >/dev/null 2>/dev/null
    fi
}

trap cleanup EXIT
python jms start all
