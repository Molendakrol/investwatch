#!/usr/bin/env bash
# Runs the whole stack locally without Docker (Python 3.11+ and Node 20+).
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r services/api/requirements.txt -r services/analyzer/requirements.txt -r services/worker/requirements.txt
(cd frontend && npm ci --silent && npm run build)
export INTERNAL_TOKEN="${INTERNAL_TOKEN:-dev-internal-token}" DEMO_SITE_URL="${DEMO_SITE_URL:-http://localhost:8080}"
trap 'kill 0' EXIT
.venv/bin/python -m http.server 8080 --directory demo-sites/site >/dev/null 2>&1 &
(cd services/analyzer && API_URL=http://localhost:8000 ../../.venv/bin/uvicorn analyzer.app:app --port 8001) &
(cd services/api && ANALYZER_URL=http://localhost:8001 ../../.venv/bin/uvicorn app.main:app --port 8000) &
(cd services/worker && sleep 3 && API_URL=http://localhost:8000 ANALYZER_URL=http://localhost:8001 ../../.venv/bin/python -m worker.main) &
(cd frontend && npm run dev -- --port 5173) &
wait
