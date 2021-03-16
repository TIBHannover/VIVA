#!/bin/bash
# echo "Running shellscript updated" 
# ls -l
trap 'exit 0' SIGTERM
conda run --no-capture-output  -p  /conda_env exec gunicorn --chdir src/ faiss_service:__hug_wsgi__ -b 0.0.0.0:8001 --reload --timeout 60 &
#conda run -no-capture-output -n faiss_env hug -f src/faiss_service.py
while true; do sleep 1; done
