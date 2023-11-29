#!/bin/bash

set -e

test -e /tmp/worker_ready_ansible
test -e /tmp/worker_ready_celery
test -e /tmp/worker_heartbeat_ansible && test $(($(date +%s) - $(stat -c %Y /tmp/worker_heartbeat_ansible))) -lt 20
test -e /tmp/worker_heartbeat_celery && test $(($(date +%s) - $(stat -c %Y /tmp/worker_heartbeat_celery))) -lt 20
