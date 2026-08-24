#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required" >&2
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo "Starting services..."
docker compose up -d

echo "Waiting for backend health..."
ok=0
for i in $(seq 1 60); do
  if curl -fsS "http://localhost:8000/health" >/dev/null 2>&1 \
    || curl -fsS "http://localhost:8000/api/health" >/dev/null 2>&1; then
    echo "Backend is healthy"
    ok=1
    break
  fi
  sleep 2
done
if [ "$ok" != "1" ]; then
  echo "Timeout waiting for backend health" >&2
  exit 1
fi

python demo/import_demo_data.py
echo "Demo ready: http://localhost  (demo_admin / Demo@2026!)"
echo "Do not commit .env, kubeconfig, or SSH keys."
