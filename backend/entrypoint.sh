#!/bin/sh
set -e
if [ "${SEED_DEMO:-false}" = "true" ]; then
  echo "Seeding demo users and sample documents..."
  python -m app.seed
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
