"""Repository for user_tasks table."""

import json
from typing import Any, Dict, List, Optional

from src.db import get_db

_COLUMNS = (
    "id, user_id, type, name, cron_expression, is_active, config, "
    "llm_provider_id, llm_model, last_run_at, last_status, next_run_at, "
    "created_at, updated_at"
)


def _row_to_dict(row) -> Dict[str, Any]:
    d = dict(row)
    if isinstance(d.get("config"), str):
        d["config"] = json.loads(d["config"])
    return d


class UserTaskRepository:

    @staticmethod
    async def get_all(user_id: str) -> List[Dict[str, Any]]:
        db = get_db()
        rows = await db.fetch_all(
            f"SELECT {_COLUMNS} FROM user_tasks WHERE user_id = $1 ORDER BY created_at DESC",
            user_id,
        )
        return [_row_to_dict(r) for r in rows]

    @staticmethod
    async def get(task_id: int) -> Optional[Dict[str, Any]]:
        db = get_db()
        row = await db.fetch_one(f"SELECT {_COLUMNS} FROM user_tasks WHERE id = $1", task_id)
        return _row_to_dict(row) if row else None

    @staticmethod
    async def get_active_tasks() -> List[Dict[str, Any]]:
        db = get_db()
        rows = await db.fetch_all(
            f"SELECT {_COLUMNS} FROM user_tasks WHERE is_active = true ORDER BY next_run_at ASC NULLS FIRST"
        )
        return [_row_to_dict(r) for r in rows]

    @staticmethod
    async def create(data: Dict[str, Any]) -> Dict[str, Any]:
        db = get_db()
        config_json = json.dumps(data.get("config") or {})
        row = await db.fetch_one(
            f"""
            INSERT INTO user_tasks (user_id, type, name, cron_expression, is_active, config, llm_provider_id, llm_model)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8)
            RETURNING {_COLUMNS}
            """,
            data["user_id"],
            data["type"],
            data["name"],
            data["cron_expression"],
            data.get("is_active", True),
            config_json,
            data.get("llm_provider_id"),
            data.get("llm_model"),
        )
        return _row_to_dict(row)

    @staticmethod
    async def update(task_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        db = get_db()
        updates, values, n = [], [], 1
        for field, col in [
            ("name", "name"), ("cron_expression", "cron_expression"),
            ("is_active", "is_active"), ("last_status", "last_status"),
        ]:
            if field in data and data[field] is not None:
                updates.append(f"{col} = ${n}")
                values.append(data[field])
                n += 1
        if "config" in data and data["config"] is not None:
            updates.append(f"config = ${n}::jsonb")
            values.append(json.dumps(data["config"]))
            n += 1
        if "last_run_at" in data:
            updates.append(f"last_run_at = ${n}")
            values.append(data["last_run_at"])
            n += 1
        if not updates:
            return await UserTaskRepository.get(task_id)
        updates.append("updated_at = NOW()")
        values.append(task_id)
        row = await db.fetch_one(
            f"UPDATE user_tasks SET {', '.join(updates)} WHERE id = ${n} RETURNING {_COLUMNS}",
            *values,
        )
        return _row_to_dict(row) if row else None

    @staticmethod
    async def delete(task_id: int) -> bool:
        db = get_db()
        result = await db.execute("DELETE FROM user_tasks WHERE id = $1", task_id)
        return result == "DELETE 1"

    @staticmethod
    async def request_run_now(task_id: int) -> None:
        db = get_db()
        await db.execute(
            "INSERT INTO user_task_run_now (task_id) VALUES ($1) ON CONFLICT (task_id) DO UPDATE SET requested_at = NOW()",
            task_id,
        )
