#!/usr/bin/env bash
set -o errexit

# Start the FastAPI server with Uvicorn
python -m uvicorn app:app --host 0.0.0.0 --port 10000
