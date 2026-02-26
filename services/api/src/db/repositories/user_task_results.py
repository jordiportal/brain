"""Repository for user_task_results — per-user SQLite."""

import json
from typing import Any, Dict, List, Optional

from src.db.user_db import user_db, row_to_dict

_COLUMNS = "id, task_id, result_type, title, content, data, is_read, created_at, expires_at"


def _normalise(row: dict) -> dict:
    d = dict(row)
    if isinstance(d.get("data"), str):
        try:
            d["data"] = json.loads(d["data"])
        except (json.JSONDecodeError, TypeError):
            pass
    d["is_read"] = bool(d.get("is_read"))
    return d


class UserTaskResultRepository:

    @staticmethod
    async def get_unread(user_id: str) -> List[Dict[str, Any]]:
        conn = await user_db.get_connection(user_id)
        async with conn.execute(
            f"SELECT {_COLUMNS} FROM user_task_results "
            "WHERE is_read = 0 AND expires_at > datetime('now') "
            "ORDER BY created_at ASC"
        ) as cur:
            rows = await cur.fetchall()
        return [_normalise(row_to_dict(r)) for r in rows]

    @staticmethod
    async def mark_as_read(user_id: str) -> int:
        conn = await user_db.get_connection(user_id)
        cur = await conn.execute(
            "UPDATE user_task_results SET is_read = 1 WHERE is_read = 0"
        )
        await conn.commit()
        return cur.rowcount

    @staticmethod
    async def create(
        user_id: str,
        task_id: int,
        result_type: str,
        title: str,
        content: str,
        data: Optional[Dict] = None,
        expires_at_days: int = 7,
    ) -> Dict[str, Any]:
        conn = await user_db.get_connection(user_id)
        data_json = json.dumps(data) if data else "{}"
        async with conn.execute(
            f"""
            INSERT INTO user_task_results (task_id, result_type, title, content, data, expires_at)
            VALUES (?, ?, ?, ?, ?, datetime('now', '+' || ? || ' days'))
            RETURNING {_COLUMNS}
            """,
            (task_id, result_type, title, content, data_json, str(expires_at_days)),
        ) as cur:
            row = await cur.fetchone()
        await conn.commit()
        return _normalise(row_to_dict(row)) if row else {}

    @staticmethod
    async def get_by_task(user_id: str, task_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        conn = await user_db.get_connection(user_id)
        async with conn.execute(
            f"SELECT {_COLUMNS} FROM user_task_results WHERE task_id = ? ORDER BY created_at DESC LIMIT ?",
            (task_id, limit),
        ) as cur:
            rows = await cur.fetchall()
        return [_normalise(row_to_dict(r)) for r in rows]

    @staticmethod
    async def cleanup_expired(user_id: str) -> int:
        conn = await user_db.get_connection(user_id)
        cur = await conn.execute(
            "DELETE FROM user_task_results WHERE expires_at <= datetime('now')"
        )
        await conn.commit()
        return cur.rowcount
