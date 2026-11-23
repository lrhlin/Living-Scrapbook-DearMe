#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if ! command -v node >/dev/null 2>&1; then
  echo "Install Node.js 24 or later, then run this script again."
  exit 1
fi
if [ ! -x backend/venv/bin/python ]; then
  DEARME_PYTHON_BIN="${DEARME_PYTHON:-}"
  if [ -z "$DEARME_PYTHON_BIN" ]; then
    for candidate in python3.12 python3.13 python3.11; do
      if command -v "$candidate" >/dev/null 2>&1 && "$candidate" --version >/dev/null 2>&1; then
        DEARME_PYTHON_BIN="$candidate"
        break
      fi
    done
  fi
  if [ -z "$DEARME_PYTHON_BIN" ] && [ -x "$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3" ]; then
    DEARME_PYTHON_BIN="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
  fi
  if [ -z "$DEARME_PYTHON_BIN" ]; then
    echo "Install Python 3.11–3.13, or set DEARME_PYTHON to a compatible executable."
    exit 1
  fi
  "$DEARME_PYTHON_BIN" -m venv backend/venv
fi
REQ_HASH="$(backend/venv/bin/python -c 'import hashlib; print(hashlib.sha256(open("backend/requirements.txt","rb").read()).hexdigest())')"
if [ ! -f backend/venv/.dearme-requirements ] || [ "$(cat backend/venv/.dearme-requirements)" != "$REQ_HASH" ]; then
  PIP_DISABLE_PIP_VERSION_CHECK=1 backend/venv/bin/python -m pip install -r backend/requirements.txt
  echo "$REQ_HASH" > backend/venv/.dearme-requirements
fi
TOOLS_HASH="$(backend/venv/bin/python -c 'import hashlib; print(hashlib.sha256(open("tools/package.json","rb").read()).hexdigest())')"
if [ ! -f tools/node_modules/.dearme-dependencies ] || [ "$(cat tools/node_modules/.dearme-dependencies)" != "$TOOLS_HASH" ]; then
  npm install --prefix tools --ignore-scripts --no-audit --no-fund
  echo "$TOOLS_HASH" > tools/node_modules/.dearme-dependencies
fi
echo ""
echo "Dear Me · Living Scrapbook"
echo "Open http://127.0.0.1:${DEARME_PORT:-8000}"
echo "Generating a sticker sends the photo to IBM Bob and uses Bobcoins."
echo ""
cd backend
exec venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "${DEARME_PORT:-8000}"
