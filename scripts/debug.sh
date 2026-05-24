#!/usr/bin/env bash
# Starts the frontend container only. Run the backend via the Cursor/VS Code
# debugger using the "Backend: FastAPI" launch configuration.
set -e
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then cp .env.example .env; fi
mkdir -p data
docker compose up -d "$@" frontend
echo "Frontend running at http://localhost:3000"
docker compose stop backend
echo "Start the backend via the 'Backend: FastAPI' debugger in Cursor/VS Code."
