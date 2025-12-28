#!/usr/bin/env bash
set -o errexit

# Debug: show all environment variables related to port
echo "Render environment variables:"
env | grep PORT || echo "No PORT variable found."

# Use Render’s dynamic PORT if provided, else default to 10000 (for local dev)
PORT=${PORT:-10000}

echo "Starting FastAPI with Uvicorn on port: $PORT"
exec uvicorn app:app --host 0.0.0.0 --port "$PORT"
