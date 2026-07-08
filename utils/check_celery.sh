#!/bin/bash

set -e

function check_state() {
    file=$1
    test -e $1
    if [[ $? -ne 0 ]]; then
        return 1
    fi
    test $(($(date +%s) - $(stat -c %Y $1))) -lt 20
    if [[ $? -ne 0 ]]; then
	    v=$(($(date +%s) - $(stat -c %Y $1)))
	    echo $v
        return 1
    fi
    return 0
}

combine='/tmp/worker_heartbeat_ansible,celery'
if [[ -f $combine ]]; then
    check_state $combine
else
    check_state /tmp/worker_heartbeat_ansible
    check_state /tmp/worker_heartbeat_celery
fi