#!/usr/bin/env bash
# Start the FastAPI backend
set -e
cd "$(dirname "$0")/backend"
if [ ! -d "venv" ]; then
  echo "Creating virtualenv..."
  python3 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt -q
else
  source venv/bin/activate
fi
echo "Starting backend at http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
uvicorn app.main:app --reload --port 8000
