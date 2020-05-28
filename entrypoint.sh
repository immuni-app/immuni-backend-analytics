#!/bin/bash

set -eu

CELERY_WORKER_CONCURRENCY=${CELERY_WORKER_CONCURRENCY:-2}

case "$1" in
    beat) poetry run celery beat \
            --app=immuni_analytics.celery.celery_app \
            --loglevel=debug ;;
    worker) poetry run celery worker \
            --app=immuni_analytics.celery.celery_app \
            --concurrency=${CELERY_WORKER_CONCURRENCY} \
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
