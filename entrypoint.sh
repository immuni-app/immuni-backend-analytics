#!/bin/bash

set -eu

API_HOST=0.0.0.0
API_PORT=${API_PORT:-5000}
API_WORKERS=${API_WORKERS:-3}
API_WORKER_MAX_REQUESTS=${API_WORKER_MAX_REQUESTS:-10000}
CELERY_WORKER_CONCURRENCY=${CELERY_WORKER_CONCURRENCY:-2}

case "$1" in
    api) poetry run gunicorn immuni_analytics.sanic:sanic_app \
            --access-logfile='-' \
            --bind=${API_HOST}:${API_PORT} \
            --max-requests=${API_WORKER_MAX_REQUESTS} \
            --workers=${API_WORKERS} \
            --worker-class=uvicorn.workers.UvicornWorker ;;
    beat) poetry run celery beat \
            --app=immuni_analytics.celery.celery_app \
            --loglevel=debug ;;
    worker) poetry run celery worker \
            --app=immuni_analytics.celery.celery_app \
            --concurrency=${CELERY_WORKER_CONCURRENCY} \
            --queues=${CELERY_WORKER_QUEUE} \
            --hostname=${CELERY_WORKER_QUEUE} \
            --task-events \
            --without-gossip \
            --without-mingle \
            --without-heartbeat \
            --loglevel=debug ;;
    debug) echo "Running in debug mode ..." \
            && tail -f /dev/null ;;  # Allow entering the container to inspect the environment.
    *) echo "Received unknown command $1 (allowed: api, beat, worker)"
       exit 2 ;;
esac
