#!/bin/bash
while !</dev/tcp/${SERVICE_DATABASE_REDIS}/6379; do sleep 1; done
while !</dev/tcp/${SERVICE_DATABASE_POSTGRES}/5432; do sleep 1; done
python manage.py migrate
python manage.py collectstatic --no-input --clear
PROC_COUNT=$(nproc)
WORKERS=$((PROC_COUNT<16 ? PROC_COUNT : 16))
exec gunicorn viva.wsgi:application --bind 0.0.0.0:8000 --workers "${WORKERS}" --timeout "${DJANGO_SERVICE_TIMEOUT}"