#!/usr/bin/env bash
set -o errexit

# Start the FastAPI server with Uvicorn using Render's dynamic PORT
if [ -z "$PORT" ]; then
  PORT=10000
fi

echo "Starting FastAPI with Uvicorn on port: $PORT"
exec uvicorn app:app --host 0.0.0.0 --port $PORT

