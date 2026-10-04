#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  uv venv --python 3.9
fi

uv pip install --python .venv/bin/python -r requirements.txt
exec .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port "${PORT:-8000}"
