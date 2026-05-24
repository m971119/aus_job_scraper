#!/usr/bin/env bash
# Apply all pending database migrations.
set -e
cd "$(dirname "$0")/../backend"
uv run alembic upgrade head
