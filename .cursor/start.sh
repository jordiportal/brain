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

echo "==> [start] Ready: PostgreSQL:$PGPORT (db=$POSTGRES_DB) + Redis:$REDIS_PORT"
