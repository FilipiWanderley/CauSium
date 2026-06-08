#!/bin/bash
export PYTHONPATH=/home/site/wwwroot:/home/site/wwwroot/antenv/lib/python3.12/site-packages
cd /home/site/wwwroot
exec /home/site/wwwroot/antenv/bin/python -m gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 2 --timeout 600