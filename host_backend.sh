#!/bin/bash
set -e

cd backend

echo "🚀 Starting FastAPI server on http://localhost:8000 ..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
