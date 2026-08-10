#!/usr/bin/env bash
# ===========================================
# Brain - Cloud Agent start script
# Per-boot reconciliation: brings up PostgreSQL (pgvector) and Redis,
# creates the role/database, and applies the SQL init scripts once.
# Idempotent and safe to re-run. Returns after services are ready.
# ===========================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BRAIN_DATA="${BRAIN_DATA:-$HOME/brain-data}"
PGDATA="$BRAIN_DATA/pgdata"
PGBIN="/usr/lib/postgresql/16/bin"
PGPORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-brain_db}"
POSTGRES_USER="${POSTGRES_USER:-brain}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-brain_secret}"
REDIS_DATA="$BRAIN_DATA/redis"
REDIS_PORT="${REDIS_PORT:-6379}"

mkdir -p "$BRAIN_DATA" "$REDIS_DATA"

# ---------------------------------------------------------------------------
# PostgreSQL + pgvector
# ---------------------------------------------------------------------------
if [ ! -s "$PGDATA/PG_VERSION" ]; then
  echo "==> [start] Initializing PostgreSQL cluster at $PGDATA"
  "$PGBIN/initdb" -D "$PGDATA" -U postgres \
    --auth-local=trust --auth-host=trust >/dev/null
  {
    echo "listen_addresses = 'localhost'"
    echo "port = $PGPORT"
    echo "unix_socket_directories = '$BRAIN_DATA'"
  } >> "$PGDATA/postgresql.conf"
fi

if ! "$PGBIN/pg_ctl" -D "$PGDATA" status >/dev/null 2>&1; then
  echo "==> [start] Starting PostgreSQL on port $PGPORT"
  "$PGBIN/pg_ctl" -D "$PGDATA" -l "$BRAIN_DATA/postgres.log" -w start
fi

PSQL="$PGBIN/psql -h $BRAIN_DATA -p $PGPORT -U postgres"

if ! $PSQL -tAc "SELECT 1 FROM pg_roles WHERE rolname='$POSTGRES_USER'" | grep -q 1; then
  echo "==> [start] Creating role '$POSTGRES_USER'"
  $PSQL -c "CREATE ROLE \"$POSTGRES_USER\" LOGIN SUPERUSER PASSWORD '$POSTGRES_PASSWORD'"
fi

if ! $PSQL -tAc "SELECT 1 FROM pg_database WHERE datname='$POSTGRES_DB'" | grep -q 1; then
  echo "==> [start] Creating database '$POSTGRES_DB'"
  $PSQL -c "CREATE DATABASE \"$POSTGRES_DB\" OWNER \"$POSTGRES_USER\""
fi

MARKER="$BRAIN_DATA/.db-initialized"
if [ ! -f "$MARKER" ]; then
  echo "==> [start] Applying database/init SQL scripts"
  for f in "$ROOT"/database/init/*.sql; do
    echo "    - $(basename "$f")"
    "$PGBIN/psql" -h "$BRAIN_DATA" -p "$PGPORT" -U "$POSTGRES_USER" \
      -d "$POSTGRES_DB" -v ON_ERROR_STOP=0 -q -f "$f" >/dev/null
  done
  touch "$MARKER"
fi

# ---------------------------------------------------------------------------
# Redis
# ---------------------------------------------------------------------------
if ! redis-cli -p "$REDIS_PORT" ping >/dev/null 2>&1; then
  echo "==> [start] Starting Redis on port $REDIS_PORT"
  redis-server --daemonize yes --dir "$REDIS_DATA" \
    --appendonly yes --port "$REDIS_PORT" >/dev/null
fi

# ---------------------------------------------------------------------------
# Application dev servers (launched in the background, then we return).
# Guards keep this idempotent: skip if the port is already served, or if the
# dependencies have not been installed yet (install.sh runs first).
# ---------------------------------------------------------------------------
port_in_use() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null && { exec 3>&-; return 0; } || return 1; }

API_BIN="$ROOT/services/api/.venv/bin/uvicorn"
if [ -x "$API_BIN" ] && ! port_in_use 8000; then
  echo "==> [start] Starting API (FastAPI) on :8000"
  ( cd "$ROOT/services/api" && \
    DATABASE_URL="postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@localhost:$PGPORT/$POSTGRES_DB" \
    REDIS_URL="redis://localhost:$REDIS_PORT" \
    OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}" \
    JWT_SECRET="${JWT_SECRET:-brain-jwt-secret-dev-only}" \
    nohup "$API_BIN" src.main:app --host 0.0.0.0 --port 8000 --reload \
      >"$BRAIN_DATA/api.log" 2>&1 & )
fi

GUI_BIN="$ROOT/services/gui/node_modules/.bin/ng"
if [ -x "$GUI_BIN" ] && ! port_in_use 4200; then
  echo "==> [start] Starting GUI (Angular) on :4200"
  ( cd "$ROOT/services/gui" && \
    nohup "$GUI_BIN" serve --host 0.0.0.0 --port 4200 --poll 2000 \
      >"$BRAIN_DATA/gui.log" 2>&1 & )
fi

echo "==> [start] Ready: PostgreSQL:$PGPORT (db=$POSTGRES_DB) + Redis:$REDIS_PORT + API:8000 + GUI:4200"
