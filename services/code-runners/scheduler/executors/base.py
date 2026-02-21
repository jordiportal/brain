"""Helpers compartidos para los ejecutores de tareas."""

import json
import os
from typing import Any, Dict, Optional

import asyncpg
import httpx

PROXY_365_URL = os.environ.get("PROXY_365_URL", "http://host.docker.internal:3001")
PROXY_365_API_KEY = os.environ.get("PROXY_365_API_KEY", "")
API_URL = os.environ.get("API_URL", "http://api:8000")


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
    # Usar la API key por defecto del Brain (se podría pasar como env)
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
    pool: asyncpg.Pool, task_id: int, user_id: str,
    result_type: str, title: str, content: str,
    data: Optional[Dict] = None, expires_days: int = 7,
) -> None:
    data_json = json.dumps(data) if data else None
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO user_task_results (task_id, user_id, result_type, title, content, data, expires_at) "
            "VALUES ($1, $2, $3, $4, $5, COALESCE($6::jsonb, '{}'::jsonb), NOW() + ($7 || ' days')::interval)",
            task_id, user_id, result_type, title, content, data_json, str(expires_days),
        )


async def get_user_profile(pool: asyncpg.Pool, user_id: str) -> Optional[Dict[str, Any]]:
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
