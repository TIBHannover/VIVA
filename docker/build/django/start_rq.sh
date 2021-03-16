#!/bin/bash
while !</dev/tcp/${SERVICE_DATABASE_REDIS}/6379; do sleep 1; done
exec python manage.py rqworker image_downloader