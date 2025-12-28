#!/usr/bin/env bash
set -o errexit

echo "Render environment variables:"
env | grep PORT || echo "No PORT variable found."

# Correct fallback syntax (use 10000 only if $PORT is missing)
PORT=${PORT:-10000}

echo "Starting FastAPI with Uvicorn on port: $PORT"
exec uvicorn app:app --host 0.0.0.0 --port "$PORT" --workers 1


