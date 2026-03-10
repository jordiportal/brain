"""
Task Repository — CRUD for engine v2 tasks.
"""

import json
import logging
from datetime import datetime
from typing import Optional

from ..connection import get_db
from ...engine.models import (
    Task, TaskState, TaskEvent, TaskFilters, Message, Artifact,
)

logger = logging.getLogger(__name__)


def _serialize_json(obj) -> str:
    """Serialize a Pydantic model or dict to JSON string."""
    if hasattr(obj, "model_dump"):
        return json.dumps(obj.model_dump(mode="json"), ensure_ascii=False, default=str)
    return json.dumps(obj, ensure_ascii=False, default=str)


def _row_to_task(row) -> Task:
    """Convert a database row to a Task model."""
    history_raw = row["history"]
    history = (
        json.loads(history_raw) if isinstance(history_raw, str) else (history_raw or [])
    )
    artifacts_raw = row["artifacts"]
    artifacts = (
        json.loads(artifacts_raw) if isinstance(artifacts_raw, str) else (artifacts_raw or [])
    )
    input_raw = row["input"]
    input_data = json.loads(input_raw) if isinstance(input_raw, str) else input_raw
    output_raw = row["output"]
    output_data = (
        json.loads(output_raw) if isinstance(output_raw, str) else output_raw
    )
    metadata_raw = row["metadata"]
    metadata = (
        json.loads(metadata_raw) if isinstance(metadata_raw, str) else (metadata_raw or {})
    )

    return Task(
        id=row["id"],
        context_id=row["context_id"],
        parent_task_id=row["parent_task_id"],
        agent_id=row["agent_id"],
        chain_id=row["chain_id"],
        state=TaskState(row["state"]),
        state_reason=row["state_reason"],
        input=Message(**input_data) if isinstance(input_data, dict) else input_data,
        output=Message(**output_data) if isinstance(output_data, dict) else None,
        history=[Message(**m) if isinstance(m, dict) else m for m in history],
        artifacts=[Artifact(**a) if isinstance(a, dict) else a for a in artifacts],
        checkpoint_thread_id=row["checkpoint_thread_id"],
        tokens_used=row["tokens_used"] or 0,
        cost_usd=float(row["cost_usd"] or 0),
        duration_ms=row["duration_ms"] or 0,
        iterations=row["iterations"] or 0,
        metadata=metadata,
        created_by=row["created_by"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        completed_at=row["completed_at"],
    )


class TaskRepository:
    """Async repository for tasks using the shared asyncpg pool."""

    @staticmethod
    async def create(task: Task) -> Task:
        db = get_db()
        await db.execute(
            """
            INSERT INTO tasks (
                id, context_id, parent_task_id, agent_id, chain_id,
                state, state_reason,
                input, output, history, artifacts,
                checkpoint_thread_id,
                tokens_used, cost_usd, duration_ms, iterations,
                metadata, created_by, created_at, updated_at, completed_at
            ) VALUES (
                $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21
            )
            """,
            task.id,
            task.context_id,
            task.parent_task_id,
            task.agent_id,
            task.chain_id,
            task.state.value,
            task.state_reason,
            _serialize_json(task.input),
            _serialize_json(task.output) if task.output else None,
            _serialize_json(task.history),
            _serialize_json(task.artifacts),
            task.checkpoint_thread_id,
            task.tokens_used,
            task.cost_usd,
            task.duration_ms,
            task.iterations,
            _serialize_json(task.metadata),
            task.created_by,
            task.created_at,
            task.updated_at,
            task.completed_at,
        )
        return task

    @staticmethod
    async def get(task_id: str) -> Optional[Task]:
        db = get_db()
        row = await db.fetch_one("SELECT * FROM tasks WHERE id = $1", task_id)
        return _row_to_task(row) if row else None

    @staticmethod
    async def list_tasks(filters: TaskFilters) -> list[Task]:
        db = get_db()
        conditions: list[str] = []
        params: list = []
        idx = 1

        if filters.context_id:
            conditions.append(f"context_id = ${idx}")
            params.append(filters.context_id)
            idx += 1
        if filters.agent_id:
            conditions.append(f"agent_id = ${idx}")
            params.append(filters.agent_id)
            idx += 1
        if filters.chain_id:
            conditions.append(f"chain_id = ${idx}")
            params.append(filters.chain_id)
            idx += 1
        if filters.parent_task_id:
            conditions.append(f"parent_task_id = ${idx}")
            params.append(filters.parent_task_id)
            idx += 1
        if filters.state:
            conditions.append(f"state = ${idx}")
            params.append(filters.state.value)
            idx += 1
        if filters.states:
            placeholders = ", ".join(f"${idx + i}" for i in range(len(filters.states)))
            conditions.append(f"state IN ({placeholders})")
            for s in filters.states:
                params.append(s.value)
                idx += 1
        if filters.created_by:
            conditions.append(f"created_by = ${idx}")
            params.append(filters.created_by)
            idx += 1

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        allowed_order = {"created_at", "updated_at", "duration_ms", "tokens_used", "state"}
        order_col = filters.order_by if filters.order_by in allowed_order else "created_at"
        order_dir = "ASC" if filters.order_dir.upper() == "ASC" else "DESC"

        query = f"""
            SELECT * FROM tasks {where}
            ORDER BY {order_col} {order_dir}
            LIMIT ${idx} OFFSET ${idx + 1}
        """
        params.extend([filters.limit, filters.offset])
        rows = await db.fetch_all(query, *params)
        return [_row_to_task(r) for r in rows]

    @staticmethod
    async def count(filters: TaskFilters) -> int:
        db = get_db()
        conditions: list[str] = []
        params: list = []
        idx = 1

        if filters.context_id:
            conditions.append(f"context_id = ${idx}")
            params.append(filters.context_id)
            idx += 1
        if filters.state:
            conditions.append(f"state = ${idx}")
            params.append(filters.state.value)
            idx += 1
        if filters.created_by:
            conditions.append(f"created_by = ${idx}")
            params.append(filters.created_by)
            idx += 1

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        row = await db.fetch_one(f"SELECT COUNT(*) as cnt FROM tasks {where}", *params)
        return row["cnt"] if row else 0

    @staticmethod
    async def update_state(
        task_id: str,
        state: TaskState,
        reason: Optional[str] = None,
        output: Optional[Message] = None,
    ) -> Optional[Task]:
        db = get_db()
        now = datetime.utcnow()
        completed_at = now if state in {TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELED} else None

        sets = ["state = $2", "state_reason = $3", "updated_at = $4"]
        params: list = [task_id, state.value, reason, now]
        idx = 5

        if completed_at:
            sets.append(f"completed_at = ${idx}")
            params.append(completed_at)
            idx += 1
        if output:
            sets.append(f"output = ${idx}")
            params.append(_serialize_json(output))
            idx += 1

        await db.execute(
            f"UPDATE tasks SET {', '.join(sets)} WHERE id = $1",
            *params,
        )
        return await TaskRepository.get(task_id)

    @staticmethod
    async def update_metrics(
        task_id: str,
        tokens_used: Optional[int] = None,
        cost_usd: Optional[float] = None,
        duration_ms: Optional[int] = None,
        iterations: Optional[int] = None,
    ):
        db = get_db()
        sets: list[str] = ["updated_at = NOW()"]
        params: list = [task_id]
        idx = 2

        if tokens_used is not None:
            sets.append(f"tokens_used = ${idx}")
            params.append(tokens_used)
            idx += 1
        if cost_usd is not None:
            sets.append(f"cost_usd = ${idx}")
            params.append(cost_usd)
            idx += 1
        if duration_ms is not None:
            sets.append(f"duration_ms = ${idx}")
            params.append(duration_ms)
            idx += 1
        if iterations is not None:
            sets.append(f"iterations = ${idx}")
            params.append(iterations)
            idx += 1

        if len(sets) > 1:
            await db.execute(
                f"UPDATE tasks SET {', '.join(sets)} WHERE id = $1",
                *params,
            )

    @staticmethod
    async def add_message(task_id: str, message: Message):
        db = get_db()
        msg_json = _serialize_json(message)
        await db.execute(
            """
            UPDATE tasks
            SET history = history || $2::jsonb,
                updated_at = NOW()
            WHERE id = $1
            """,
            task_id,
            f"[{msg_json}]",
        )

    @staticmethod
    async def add_artifact(task_id: str, artifact: Artifact):
        db = get_db()
        art_json = _serialize_json(artifact)
        await db.execute(
            """
            UPDATE tasks
            SET artifacts = artifacts || $2::jsonb,
                updated_at = NOW()
            WHERE id = $1
            """,
            task_id,
            f"[{art_json}]",
        )

    @staticmethod
    async def set_checkpoint(task_id: str, thread_id: str):
        db = get_db()
        await db.execute(
            "UPDATE tasks SET checkpoint_thread_id = $2, updated_at = NOW() WHERE id = $1",
            task_id,
            thread_id,
        )

    @staticmethod
    async def delete(task_id: str) -> bool:
        db = get_db()
        result = await db.execute("DELETE FROM tasks WHERE id = $1", task_id)
        return result and "DELETE 1" in result

    @staticmethod
    async def cleanup_old(days: int = 30) -> int:
        db = get_db()
        result = await db.execute(
            """
            DELETE FROM tasks
            WHERE state IN ('completed', 'failed', 'canceled')
              AND created_at < NOW() - INTERVAL '1 day' * $1
            """,
            days,
        )
        if result:
            count_str = result.split()[-1] if result else "0"
            try:
                return int(count_str)
            except ValueError:
                return 0
        return 0

    # ---- Task Events ----

    @staticmethod
    async def create_event(event: TaskEvent) -> TaskEvent:
        db = get_db()
        row = await db.fetch_one(
            """
            INSERT INTO task_events (task_id, state, reason, message, metadata, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, created_at
            """,
            event.task_id,
            event.state.value,
            event.reason,
            _serialize_json(event.message) if event.message else None,
            _serialize_json(event.metadata),
            event.created_at,
        )
        if row:
            event.id = row["id"]
            event.created_at = row["created_at"]
        return event

    @staticmethod
    async def get_events(task_id: str) -> list[TaskEvent]:
        db = get_db()
        rows = await db.fetch_all(
            "SELECT * FROM task_events WHERE task_id = $1 ORDER BY created_at ASC",
            task_id,
        )
        result = []
        for r in rows:
            msg_raw = r["message"]
            msg = None
            if msg_raw:
                msg_data = json.loads(msg_raw) if isinstance(msg_raw, str) else msg_raw
                msg = Message(**msg_data) if isinstance(msg_data, dict) else None
            meta_raw = r["metadata"]
            meta = json.loads(meta_raw) if isinstance(meta_raw, str) else (meta_raw or {})
            result.append(TaskEvent(
                id=r["id"],
                task_id=r["task_id"],
                state=TaskState(r["state"]),
                reason=r["reason"],
                message=msg,
                metadata=meta,
                created_at=r["created_at"],
            ))
        return result
