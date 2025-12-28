#!/usr/bin/env bash
set -o errexit

# Start the FastAPI server with Uvicorn
uvicorn app:app --host 0.0.0.0 --port 10000