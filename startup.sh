#!/bin/bash
# Startup script for Azure App Service (Linux)
# Installs Playwright Chromium and starts the FastAPI server

python -m playwright install --with-deps chromium
exec gunicorn api:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 300
