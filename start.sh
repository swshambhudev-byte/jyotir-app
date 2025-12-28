#!/usr/bin/env bash
set -o errexit

echo "Starting FastAPI with Uvicorn on Render port: ${PORT:-10000}"
exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000}
