"""Repository for user_tasks — per-user SQLite."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.db.user_db import user_db, row_to_dict

_COLUMNS = (
    "id, type, name, cron_expression, is_active, config, "
    "llm_provider_id, llm_model, last_run_at, last_status, next_run_at, "
    "created_at, updated_at"
)


def _normalise(row: dict) -> dict:
    d = dict(row)
    if isinstance(d.get("config"), str):
        try:
            d["config"] = json.loads(d["config"])
        except (json.JSONDecodeError, TypeError):
            pass
    d["is_active"] = bool(d.get("is_active"))
    return d


class UserTaskRepository:

    @staticmethod
    async def get_all(user_id: str) -> List[Dict[str, Any]]:
        conn = await user_db.get_connection(user_id)
        async with conn.execute(
            f"SELECT {_COLUMNS} FROM user_tasks ORDER BY created_at DESC"
        ) as cur:
            rows = await cur.fetchall()
        return [_normalise(row_to_dict(r)) for r in rows]

    @staticmethod
    async def get(user_id: str, task_id: int) -> Optional[Dict[str, Any]]:
        conn = await user_db.get_connection(user_id)
        async with conn.execute(
            f"SELECT {_COLUMNS} FROM user_tasks WHERE id = ?", (task_id,)
        ) as cur:
            row = await cur.fetchone()
        return _normalise(row_to_dict(row)) if row else None

    @staticmethod
    async def create(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        conn = await user_db.get_connection(user_id)
        config_json = json.dumps(data.get("config") or {})
        async with conn.execute(
            f"""
            INSERT INTO user_tasks (type, name, cron_expression, is_active, config, llm_provider_id, llm_model)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["type"],
                data["name"],
                data["cron_expression"],
                1 if data.get("is_active", True) else 0,
                config_json,
                data.get("llm_provider_id"),
                data.get("llm_model"),
            ),
        ) as cur:
            last_id = cur.lastrowid
        await conn.commit()
        return await UserTaskRepository.get(user_id, last_id)  # type: ignore[return-value]

    @staticmethod
    async def update(user_id: str, task_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        conn = await user_db.get_connection(user_id)
        updates: list[str] = []
        values: list[Any] = []
        for field, col in [
            ("name", "name"),
            ("cron_expression", "cron_expression"),
            ("last_status", "last_status"),
        ]:
            if field in data and data[field] is not None:
                updates.append(f"{col} = ?")
                values.append(data[field])
        if "is_active" in data and data["is_active"] is not None:
            updates.append("is_active = ?")
            values.append(1 if data["is_active"] else 0)
        if "config" in data and data["config"] is not None:
            updates.append("config = ?")
            values.append(json.dumps(data["config"]))
        if "last_run_at" in data:
            updates.append("last_run_at = ?")
            val = data["last_run_at"]
            values.append(val.isoformat() if isinstance(val, datetime) else val)
        if not updates:
            return await UserTaskRepository.get(user_id, task_id)
        updates.append("updated_at = datetime('now')")
        values.append(task_id)
        await conn.execute(
            f"UPDATE user_tasks SET {', '.join(updates)} WHERE id = ?",
            values,
        )
        await conn.commit()
        return await UserTaskRepository.get(user_id, task_id)

    @staticmethod
    async def delete(user_id: str, task_id: int) -> bool:
        conn = await user_db.get_connection(user_id)
        cur = await conn.execute("DELETE FROM user_tasks WHERE id = ?", (task_id,))
        await conn.commit()
        return cur.rowcount > 0

    @staticmethod
    async def request_run_now(user_id: str, task_id: int) -> None:
        conn = await user_db.get_connection(user_id)
        await conn.execute(
            "INSERT INTO user_task_run_now (task_id) VALUES (?) "
            "ON CONFLICT (task_id) DO UPDATE SET requested_at = datetime('now')",
            (task_id,),
        )
        await conn.commit()
