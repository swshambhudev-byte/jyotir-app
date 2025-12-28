#!/usr/bin/env bash
set -o errexit

# Start the FastAPI server with Uvicorn using Render's dynamic PORT
port=${PORT:-10000}
exec uvicorn app:app --host 0.0.0.0 --port "$port"
