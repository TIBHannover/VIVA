#!/bin/sh
if [ "$1" = "crond" ]; then
    trap "echo 'Stopping PostgreSQL backup service' && killall crond && exit 0" SIGTERM SIGINT
    echo "Starting PostgreSQL backup service"
    (crond -f -l 2)&
    while true; do sleep 1; done;
else
    exec -- "$@"
fi
