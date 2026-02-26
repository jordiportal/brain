"""Helpers compartidos para los ejecutores de tareas."""

import json
import os
from typing import Any, Dict, Optional

import aiosqlite
import asyncpg
import httpx

PROXY_365_URL = os.environ.get("PROXY_365_URL", "http://host.docker.internal:3001")
PROXY_365_API_KEY = os.environ.get("PROXY_365_API_KEY", "")
API_URL = os.environ.get("API_URL", "http://api:8000")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

_pg_pool: asyncpg.Pool | None = None


async def _get_pg_pool() -> asyncpg.Pool:
    global _pg_pool
    if _pg_pool is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL not set for user_profiles access")
        _pg_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2, command_timeout=30)
    return _pg_pool


async def call_proxy365(path: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    url = f"{PROXY_365_URL.rstrip('/')}{path}"
    headers = {"Authorization": f"Bearer {PROXY_365_API_KEY}"} if PROXY_365_API_KEY else {}
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url, params=params or {}, headers=headers)
        r.raise_for_status()
        return r.json()


async def call_llm(user_id: str, system_content: str, user_content: str, model: str = "brain-adaptive") -> str:
    """POST /v1/chat/completions a Brain API; devuelve respuesta del asistente."""
    url = f"{API_URL.rstrip('/')}/v1/chat/completions"
    brain_api_key = os.environ.get("BRAIN_API_KEY", "")
    headers = {"Authorization": f"Bearer {brain_api_key}"} if brain_api_key else {}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
        "user": user_id,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(url, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        return (data.get("choices", [{}])[0].get("message") or {}).get("content", "")


async def save_result(
    db_path: str, task_id: int, user_id: str,
    result_type: str, title: str, content: str,
    data: Optional[Dict] = None, expires_days: int = 7,
) -> None:
    """Save a task result into the user's SQLite database."""
    data_json = json.dumps(data) if data else "{}"
    conn = await aiosqlite.connect(db_path)
    try:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA busy_timeout=5000")
        await conn.execute(
            "INSERT INTO user_task_results (task_id, result_type, title, content, data, expires_at) "
            "VALUES (?, ?, ?, ?, ?, datetime('now', '+' || ? || ' days'))",
            (task_id, result_type, title, content, data_json, str(expires_days)),
        )
        await conn.commit()
    finally:
        await conn.close()


async def get_user_profile(db_path: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Fetch user profile from PostgreSQL (stays in shared DB)."""
    try:
        pool = await _get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT user_id, display_name, personal_prompt, timezone, preferences "
                "FROM user_profiles WHERE user_id = $1", user_id,
            )
            if not row:
                return None
            d = dict(row)
            if isinstance(d.get("preferences"), str):
                d["preferences"] = json.loads(d["preferences"])
            return d
    except Exception:
        return None
