"""
Per-user SQLite database manager.

Each user's sandbox has its own SQLite file at:
  Host:      {WORKSPACE_HOST_BASE}/{safe_user_id}/brain_data.db
  Container: /workspace/brain_data.db

Provides async connections via aiosqlite with WAL mode for
concurrent read/write from the API and the scheduler.
"""

import os
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional

import aiosqlite
import structlog

logger = structlog.get_logger()

WORKSPACE_HOST_BASE = os.getenv(
    "SANDBOX_WORKSPACE_BASE", "/Users/jordip/Docker/workspace/users"
)
DB_FILENAME = "brain_data.db"

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS user_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    cron_expression TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    config TEXT NOT NULL DEFAULT '{}',
    llm_provider_id INTEGER,
    llm_model TEXT,
    last_run_at TEXT,
    last_status TEXT,
    next_run_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS user_task_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES user_tasks(id) ON DELETE CASCADE,
    result_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    data TEXT DEFAULT '{}',
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT NOT NULL DEFAULT (datetime('now', '+7 days'))
);

CREATE TABLE IF NOT EXISTS user_task_run_now (
    task_id INTEGER NOT NULL PRIMARY KEY REFERENCES user_tasks(id) ON DELETE CASCADE,
    requested_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL,
    title TEXT,
    description TEXT,
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_size INTEGER,
    mime_type TEXT,
    conversation_id TEXT,
    agent_id TEXT,
    source TEXT NOT NULL DEFAULT 'tool_execution',
    tool_id TEXT,
    metadata TEXT DEFAULT '{}',
    parent_artifact_id INTEGER REFERENCES artifacts(id) ON DELETE SET NULL,
    version INTEGER DEFAULT 1,
    is_latest INTEGER DEFAULT 1,
    status TEXT DEFAULT 'active',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    accessed_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS artifact_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id INTEGER NOT NULL REFERENCES artifacts(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(artifact_id, tag)
);

CREATE INDEX IF NOT EXISTS idx_tasks_active ON user_tasks(is_active) WHERE is_active = 1;
CREATE INDEX IF NOT EXISTS idx_task_results_unread ON user_task_results(is_read) WHERE is_read = 0;
CREATE INDEX IF NOT EXISTS idx_task_results_expires ON user_task_results(expires_at);
CREATE INDEX IF NOT EXISTS idx_artifacts_conversation ON artifacts(conversation_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(type);
CREATE INDEX IF NOT EXISTS idx_artifacts_status ON artifacts(status) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_artifacts_latest ON artifacts(is_latest, type) WHERE is_latest = 1;
CREATE INDEX IF NOT EXISTS idx_artifacts_created ON artifacts(created_at);
CREATE INDEX IF NOT EXISTS idx_artifact_tags_tag ON artifact_tags(tag);
"""


def safe_user_dir(user_id: str) -> str:
    return user_id.lower().replace("@", "_at_").replace(".", "_")


def user_db_path(user_id: str) -> Path:
    return Path(WORKSPACE_HOST_BASE) / safe_user_dir(user_id) / DB_FILENAME


class UserDatabase:
    """Manages per-user SQLite connections with auto-init and WAL mode."""

    def __init__(self):
        self._connections: Dict[str, aiosqlite.Connection] = {}
        self._lock = asyncio.Lock()

    async def get_connection(self, user_id: str) -> aiosqlite.Connection:
        if user_id in self._connections:
            return self._connections[user_id]

        async with self._lock:
            if user_id in self._connections:
                return self._connections[user_id]

            db_path = user_db_path(user_id)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            is_new = not db_path.exists()
            conn = await aiosqlite.connect(str(db_path))
            conn.row_factory = aiosqlite.Row

            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA foreign_keys=ON")
            await conn.execute("PRAGMA busy_timeout=5000")

            if is_new:
                await conn.executescript(_SCHEMA_SQL)
                logger.info("Created user SQLite database", user_id=user_id, path=str(db_path))
            else:
                await self._ensure_schema(conn, user_id)

            self._connections[user_id] = conn
            return conn

    async def _ensure_schema(self, conn: aiosqlite.Connection, user_id: str) -> None:
        """Run CREATE IF NOT EXISTS on existing databases to handle upgrades."""
        try:
            await conn.executescript(_SCHEMA_SQL)
        except Exception as exc:
            logger.warning("Schema migration warning", user_id=user_id, error=str(exc))

    async def close(self, user_id: str) -> None:
        conn = self._connections.pop(user_id, None)
        if conn:
            await conn.close()

    async def close_all(self) -> None:
        for uid in list(self._connections):
            await self.close(uid)


# ---------------------------------------------------------------------------
# Helper: row → dict
# ---------------------------------------------------------------------------

def row_to_dict(row: aiosqlite.Row) -> Dict[str, Any]:
    """Convert an aiosqlite.Row to a plain dict."""
    return dict(row)


# ---------------------------------------------------------------------------
# Standalone helper (for scheduler / scripts that don't use the singleton)
# ---------------------------------------------------------------------------

async def open_user_db(db_path: str | Path) -> aiosqlite.Connection:
    """Open a user SQLite database directly by file path."""
    conn = await aiosqlite.connect(str(db_path))
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    await conn.execute("PRAGMA busy_timeout=5000")
    return conn


# Global singleton used by the API
user_db = UserDatabase()
