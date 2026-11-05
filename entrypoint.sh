#!/bin/bash

# 不能删掉 cleanup 会产生僵尸进程
function cleanup()
{
    local pids=`jobs -p`
    if [[ "${pids}" != ""  ]]; then
        kill ${pids} >/dev/null 2>/dev/null
    fi
}

action="${1-start}"
service="${2-all}"

trap cleanup EXIT

rm -f /opt/jumpserver/tmp/*.pid

if [[ "$action" == "bash" || "$action" == "sh" ]];then
    bash
elif [[ "$action" == "sleep" ]];then
    echo "Sleep 365 days"
    sleep 365d
else
    which cron &>/dev/null && [[ ! -f /var/run/crond.pid ]] && cron || echo ""
    service_pid=""
    service_stop_requested=0
    function forward_stop()
    {
        service_stop_requested=1
        [[ -n "${service_pid}" ]] || return
        trap '' TERM INT HUP QUIT
        kill -TERM "${service_pid}" 2>/dev/null || true
        wait "${service_pid}"
        exit $?
    }
    trap forward_stop TERM INT HUP QUIT
    python jms "${action}" "${service}" &
    service_pid=$!
    [[ "${service_stop_requested}" == "0" ]] || forward_stop
    wait "${service_pid}"
    exit $?
fi
