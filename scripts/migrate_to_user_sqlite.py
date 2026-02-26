#!/usr/bin/env python3
"""
Migration script: PostgreSQL -> per-user SQLite (brain_data.db)

Reads user_tasks, user_task_results, and artifacts from PostgreSQL,
groups them by user_id, and writes into each user's SQLite database.

Usage:
    DATABASE_URL=postgresql://brain:brain_secret@localhost:5432/brain_db \
    SANDBOX_WORKSPACE_BASE=/Users/jordip/Docker/workspace/users \
    python scripts/migrate_to_user_sqlite.py

The script is idempotent — re-running it will skip rows that already exist.
"""

import asyncio
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import asyncpg
import aiosqlite

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://brain:brain_secret@localhost:5432/brain_db")
WORKSPACE_BASE = os.environ.get("SANDBOX_WORKSPACE_BASE", "/Users/jordip/Docker/workspace/users")
DB_FILENAME = "brain_data.db"

SCHEMA_SQL = """
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


def ts(val) -> str | None:
    if val is None:
        return None
    return val.isoformat() if hasattr(val, "isoformat") else str(val)


async def migrate():
    print(f"Connecting to PostgreSQL: {DATABASE_URL[:50]}...")
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=3)

    async with pool.acquire() as conn:
        # --- user_tasks ---
        tasks = await conn.fetch(
            "SELECT id, user_id, type, name, cron_expression, is_active, config, "
            "llm_provider_id, llm_model, last_run_at, last_status, next_run_at, "
            "created_at, updated_at FROM user_tasks"
        )
        print(f"  Found {len(tasks)} tasks in PostgreSQL")

        # --- user_task_results ---
        results = await conn.fetch(
            "SELECT id, task_id, user_id, result_type, title, content, data, "
            "is_read, created_at, expires_at FROM user_task_results"
        )
        print(f"  Found {len(results)} task results in PostgreSQL")

        # --- artifacts ---
        artifacts = await conn.fetch("SELECT * FROM artifacts")
        print(f"  Found {len(artifacts)} artifacts in PostgreSQL")

        # --- artifact_tags ---
        tags = await conn.fetch("SELECT * FROM artifact_tags")
        print(f"  Found {len(tags)} artifact tags in PostgreSQL")

    # Group by user_id
    tasks_by_user: dict[str, list] = defaultdict(list)
    for t in tasks:
        tasks_by_user[t["user_id"]].append(t)

    results_by_task: dict[int, list] = defaultdict(list)
    for r in results:
        results_by_task[r["task_id"]].append(r)

    # Artifacts: determine user from metadata or default
    artifacts_by_user: dict[str, list] = defaultdict(list)
    for a in artifacts:
        uid = "default"
        meta = a.get("metadata")
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        if isinstance(meta, dict) and meta.get("user_id"):
            uid = meta["user_id"]
        elif a.get("user_id"):
            uid = str(a["user_id"])
        artifacts_by_user[uid].append(a)

    tags_by_artifact_id: dict[int, list] = defaultdict(list)
    for t in tags:
        tags_by_artifact_id[t["artifact_id"]].append(t)

    all_users = set(tasks_by_user.keys()) | set(artifacts_by_user.keys())
    print(f"\n  Users to migrate: {len(all_users)}")

    for uid in sorted(all_users):
        user_dir = Path(WORKSPACE_BASE) / safe_user_dir(uid)
        user_dir.mkdir(parents=True, exist_ok=True)
        db_path = user_dir / DB_FILENAME

        print(f"\n  === {uid} ({db_path}) ===")

        conn = await aiosqlite.connect(str(db_path))
        try:
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA foreign_keys=ON")
            await conn.executescript(SCHEMA_SQL)

            # Migrate tasks (preserve original IDs)
            user_tasks = tasks_by_user.get(uid, [])
            pg_to_sqlite_task_id: dict[int, int] = {}

            for t in user_tasks:
                config_val = t["config"]
                if isinstance(config_val, dict):
                    config_val = json.dumps(config_val)
                elif config_val is None:
                    config_val = "{}"

                async with conn.execute(
                    "INSERT OR IGNORE INTO user_tasks "
                    "(type, name, cron_expression, is_active, config, llm_provider_id, llm_model, "
                    "last_run_at, last_status, next_run_at, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        t["type"], t["name"], t["cron_expression"],
                        1 if t["is_active"] else 0,
                        config_val,
                        t["llm_provider_id"], t["llm_model"],
                        ts(t["last_run_at"]), t["last_status"], ts(t["next_run_at"]),
                        ts(t["created_at"]), ts(t["updated_at"]),
                    ),
                ) as cur:
                    if cur.lastrowid:
                        pg_to_sqlite_task_id[t["id"]] = cur.lastrowid

            await conn.commit()
            print(f"    Tasks: {len(user_tasks)} migrated")

            # Migrate task results
            result_count = 0
            for pg_task_id, sqlite_task_id in pg_to_sqlite_task_id.items():
                for r in results_by_task.get(pg_task_id, []):
                    data_val = r["data"]
                    if isinstance(data_val, dict):
                        data_val = json.dumps(data_val)
                    elif data_val is None:
                        data_val = "{}"

                    await conn.execute(
                        "INSERT OR IGNORE INTO user_task_results "
                        "(task_id, result_type, title, content, data, is_read, created_at, expires_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            sqlite_task_id, r["result_type"], r["title"], r["content"],
                            data_val, 1 if r["is_read"] else 0,
                            ts(r["created_at"]), ts(r["expires_at"]),
                        ),
                    )
                    result_count += 1
            await conn.commit()
            print(f"    Task results: {result_count} migrated")

            # Migrate artifacts
            user_artifacts = artifacts_by_user.get(uid, [])
            pg_to_sqlite_artifact_id: dict[int, int] = {}

            for a in user_artifacts:
                meta = a.get("metadata")
                if isinstance(meta, dict):
                    meta = json.dumps(meta)
                elif meta is None:
                    meta = "{}"

                async with conn.execute(
                    "INSERT OR IGNORE INTO artifacts "
                    "(artifact_id, type, title, description, file_path, file_name, "
                    "file_size, mime_type, conversation_id, agent_id, source, tool_id, "
                    "metadata, parent_artifact_id, version, is_latest, status, "
                    "created_at, updated_at, accessed_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        a["artifact_id"], a["type"], a.get("title"), a.get("description"),
                        a["file_path"], a["file_name"], a.get("file_size"), a.get("mime_type"),
                        a.get("conversation_id"), a.get("agent_id"),
                        a.get("source", "tool_execution"), a.get("tool_id"),
                        meta, None,
                        a.get("version", 1), 1 if a.get("is_latest", True) else 0,
                        a.get("status", "active"),
                        ts(a.get("created_at")), ts(a.get("updated_at")), ts(a.get("accessed_at")),
                    ),
                ) as cur:
                    if cur.lastrowid:
                        pg_to_sqlite_artifact_id[a["id"]] = cur.lastrowid

            await conn.commit()
            print(f"    Artifacts: {len(user_artifacts)} migrated")

            # Migrate artifact tags
            tag_count = 0
            for pg_art_id, sqlite_art_id in pg_to_sqlite_artifact_id.items():
                for tag in tags_by_artifact_id.get(pg_art_id, []):
                    await conn.execute(
                        "INSERT OR IGNORE INTO artifact_tags (artifact_id, tag, created_at) VALUES (?, ?, ?)",
                        (sqlite_art_id, tag["tag"], ts(tag.get("created_at"))),
                    )
                    tag_count += 1
            await conn.commit()
            print(f"    Artifact tags: {tag_count} migrated")

        finally:
            await conn.close()

    await pool.close()
    print("\n  Migration complete!")


if __name__ == "__main__":
    asyncio.run(migrate())
