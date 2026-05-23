#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then cp .env.example .env; fi
mkdir -p data
docker compose up --build -d
echo "Running - frontend: http://localhost:3000"
