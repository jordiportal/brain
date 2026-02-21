"""Repository for user_task_results table."""

import json
from typing import Any, Dict, List, Optional

from src.db import get_db

_COLUMNS = "id, task_id, user_id, result_type, title, content, data, is_read, created_at, expires_at"


def _row_to_dict(row) -> Dict[str, Any]:
    d = dict(row)
    if isinstance(d.get("data"), str):
        d["data"] = json.loads(d["data"])
    return d


class UserTaskResultRepository:

    @staticmethod
    async def get_unread(user_id: str) -> List[Dict[str, Any]]:
        db = get_db()
        rows = await db.fetch_all(
            f"SELECT {_COLUMNS} FROM user_task_results "
            "WHERE user_id = $1 AND is_read = false AND expires_at > NOW() "
            "ORDER BY created_at ASC",
            user_id,
        )
        return [_row_to_dict(r) for r in rows]

    @staticmethod
    async def mark_as_read(user_id: str) -> int:
        db = get_db()
        result = await db.execute(
            "UPDATE user_task_results SET is_read = true WHERE user_id = $1 AND is_read = false",
            user_id,
        )
        return int(result.split()[-1]) if isinstance(result, str) and result.startswith("UPDATE") else 0

    @staticmethod
    async def create(
        task_id: int,
        user_id: str,
        result_type: str,
        title: str,
        content: str,
        data: Optional[Dict] = None,
        expires_at_days: int = 7,
    ) -> Dict[str, Any]:
        db = get_db()
        data_json = json.dumps(data) if data else None
        row = await db.fetch_one(
            f"""
            INSERT INTO user_task_results (task_id, user_id, result_type, title, content, data, expires_at)
            VALUES ($1, $2, $3, $4, $5, COALESCE($6::jsonb, '{{}}'::jsonb), NOW() + ($7 || ' days')::interval)
            RETURNING {_COLUMNS}
            """,
            task_id, user_id, result_type, title, content, data_json, expires_at_days,
        )
        return _row_to_dict(row)

    @staticmethod
    async def get_by_task(task_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        db = get_db()
        rows = await db.fetch_all(
            f"SELECT {_COLUMNS} FROM user_task_results WHERE task_id = $1 ORDER BY created_at DESC LIMIT $2",
            task_id, limit,
        )
        return [_row_to_dict(r) for r in rows]

    @staticmethod
    async def cleanup_expired() -> int:
        db = get_db()
        result = await db.execute("DELETE FROM user_task_results WHERE expires_at <= NOW()")
        return int(result.split()[-1]) if isinstance(result, str) and result.startswith("DELETE") else 0
