#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then cp .env.example .env; fi
mkdir -p backend/data
bash "$(dirname "$0")/migrate.sh"
docker compose -f docker-compose.yml -f docker-compose.dev.yml up "$@"
echo "Running (dev) - frontend: http://localhost:3000"
