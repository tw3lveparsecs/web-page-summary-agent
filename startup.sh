#!/usr/bin/env bash
set -e

# Install Playwright Chromium browser if not already present.
# Uses --with-deps to pull OS-level libraries on first run.
# If the install fails (e.g. transient package-repo issues), the
# script continues — a previous install may still be cached.
if ! python -m playwright install --with-deps chromium; then
    echo "WARNING: playwright install failed — continuing with existing browser (if any)"
fi

exec gunicorn api:app \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 300
