#!/bin/sh
set -eu
# Startup lifespan runs locked Alembic migrations before accepting traffic.
# Render supplies PORT; access logs stay off to avoid candidate URLs in logs.
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers 1 --no-access-log