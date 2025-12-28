#!/usr/bin/env bash
set -o errexit

# Log what the PORT variable actually is
echo "Render assigned PORT = $PORT"

# Use Render's dynamic port if defined, otherwise default to 10000
if [ -z "$PORT" ]; then
  PORT=10000
fi

echo "Starting FastAPI with Uvicorn on port: $PORT"
exec uvicorn app:app --host 0.0.0.0 --port "$PORT"
