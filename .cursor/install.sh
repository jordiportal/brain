#!/usr/bin/env bash
# ===========================================
# Brain - Cloud Agent install script
# Idempotent dependency setup for the API (Python) and GUI (Angular).
# Runs after the repository is checked out. Must terminate.
# ===========================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> [install] Python API dependencies"
# The API pins dependencies (e.g. unstructured==0.12.4) that require Python 3.11,
# matching services/api/Dockerfile (python:3.11-slim).
PYTHON_BIN="${PYTHON_BIN:-python3.11}"
VENV="$ROOT/services/api/.venv"
if [ ! -x "$VENV/bin/python" ]; then
  rm -rf "$VENV"
  "$PYTHON_BIN" -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install --upgrade pip wheel setuptools

# Install the CPU build of torch first so that sentence-transformers does not
# pull the multi-GB CUDA build. The browser/GPU stack is provided separately.
pip install --index-url https://download.pytorch.org/whl/cpu torch

pip install -r "$ROOT/services/api/requirements.txt"
deactivate

echo "==> [install] GUI (Angular) dependencies"
cd "$ROOT/services/gui"
# --legacy-peer-deps is required by @swimlane/ngx-graph (see Dockerfile).
npm install --legacy-peer-deps --no-audit --no-fund

echo "==> [install] Done"
