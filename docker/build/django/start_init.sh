#!/bin/bash
while !</dev/tcp/${SERVICE_DATABASE_POSTGRES}/5432; do sleep 1; done
python manage.py flush --no-input
python manage.py migrate