#!/usr/bin/env bash
set -o errexit

# Use Render’s dynamic PORT if provided, otherwise default to 10000 for local dev
PORT=${PORT:-10000}

echo "Starting FastAPI with Uvicorn on port: $PORT"
exec uvicorn app:app --host 0.0.0.0 --port "$PORT"
