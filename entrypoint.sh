#!/bin/bash
#

rm -f /opt/jumpserver/tmp/*.pid

case "$1" in
    start|init_db|upgrade_db)
        set -- /opt/jumpserver/jms "$@"
        ;;
esac

exec "$@"