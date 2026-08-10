#!/usr/bin/env bash
# ===========================================
# Brain - Cloud Agent system provisioning
# Installs the stable system toolchain the dev stack needs:
#   - Python 3.11 (matches services/api/Dockerfile; pins require <3.12)
#   - PostgreSQL 16 + pgvector
#   - Redis
#   - build tooling for Python native deps
# Idempotent: if everything is already present (e.g. the environment booted
# from a snapshot/image that already has them), this is a no-op.
# ===========================================
set -euo pipefail

need_apt=0
command -v python3.11        >/dev/null 2>&1 || need_apt=1
[ -x /usr/lib/postgresql/16/bin/postgres ] || need_apt=1
command -v redis-server      >/dev/null 2>&1 || need_apt=1

if [ "$need_apt" -eq 0 ]; then
  echo "==> [provision] System dependencies already present, skipping apt"
  exit 0
fi

if command -v sudo >/dev/null 2>&1; then SUDO="sudo"; else SUDO=""; fi
export DEBIAN_FRONTEND=noninteractive

echo "==> [provision] Installing base build tooling"
$SUDO apt-get update -qq
$SUDO apt-get install -y -qq \
  software-properties-common curl ca-certificates gnupg git \
  build-essential libpq-dev

echo "==> [provision] Adding deadsnakes PPA for Python 3.11"
$SUDO add-apt-repository -y ppa:deadsnakes/ppa
$SUDO apt-get update -qq

echo "==> [provision] Installing Python 3.11, PostgreSQL 16 + pgvector, Redis"
$SUDO apt-get install -y -qq \
  python3.11 python3.11-venv python3.11-dev \
  postgresql-16 postgresql-16-pgvector postgresql-client-16 \
  redis-server

# Node.js is normally provided by the base image; only install if missing.
if ! command -v node >/dev/null 2>&1; then
  echo "==> [provision] Installing Node.js 20"
  curl -fsSL https://deb.nodesource.com/setup_20.x | $SUDO -E bash -
  $SUDO apt-get install -y -qq nodejs
fi

echo "==> [provision] Done"
