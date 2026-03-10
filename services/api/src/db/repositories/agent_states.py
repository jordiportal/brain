"""
Agent State Repository — Persistent typed state per agent+context.
"""

import json
import logging
from typing import Optional

from ..connection import get_db
from ...engine.models import AgentState

logger = logging.getLogger(__name__)


class AgentStateRepository:
    """Repository for persisting agent state across sessions."""

    @staticmethod
    async def get(agent_id: str, context_id: str) -> Optional[AgentState]:
        db = get_db()
        row = await db.fetch_one(
            "SELECT * FROM agent_states WHERE agent_id = $1 AND context_id = $2",
            agent_id, context_id,
        )
        if not row:
            return None

        state_raw = row["state"]
        state = json.loads(state_raw) if isinstance(state_raw, str) else (state_raw or {})

        return AgentState(
            agent_id=row["agent_id"],
            context_id=row["context_id"],
            state=state,
            updated_at=row["updated_at"],
        )

    @staticmethod
    async def upsert(agent_state: AgentState) -> AgentState:
        db = get_db()
        state_json = json.dumps(agent_state.state, ensure_ascii=False, default=str)
        await db.execute(
            """
            INSERT INTO agent_states (agent_id, context_id, state, updated_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (agent_id, context_id) DO UPDATE
            SET state = $3, updated_at = NOW()
            """,
            agent_state.agent_id,
            agent_state.context_id,
            state_json,
        )
        return agent_state

    @staticmethod
    async def update_partial(agent_id: str, context_id: str, updates: dict) -> Optional[AgentState]:
        """Merge updates into existing state (JSON merge)."""
        db = get_db()
        updates_json = json.dumps(updates, ensure_ascii=False, default=str)
        await db.execute(
            """
            INSERT INTO agent_states (agent_id, context_id, state, updated_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (agent_id, context_id) DO UPDATE
            SET state = agent_states.state || $3::jsonb, updated_at = NOW()
            """,
            agent_id, context_id, updates_json,
        )
        return await AgentStateRepository.get(agent_id, context_id)

    @staticmethod
    async def delete(agent_id: str, context_id: str) -> bool:
        db = get_db()
        result = await db.execute(
            "DELETE FROM agent_states WHERE agent_id = $1 AND context_id = $2",
            agent_id, context_id,
        )
        return result and "DELETE 1" in result

    @staticmethod
    async def list_by_agent(agent_id: str) -> list[AgentState]:
        db = get_db()
        rows = await db.fetch_all(
            "SELECT * FROM agent_states WHERE agent_id = $1 ORDER BY updated_at DESC",
            agent_id,
        )
        result = []
        for r in rows:
            state_raw = r["state"]
            state = json.loads(state_raw) if isinstance(state_raw, str) else (state_raw or {})
            result.append(AgentState(
                agent_id=r["agent_id"],
                context_id=r["context_id"],
                state=state,
                updated_at=r["updated_at"],
            ))
        return result

    @staticmethod
    async def list_by_context(context_id: str) -> list[AgentState]:
        db = get_db()
        rows = await db.fetch_all(
            "SELECT * FROM agent_states WHERE context_id = $1 ORDER BY updated_at DESC",
            context_id,
        )
        result = []
        for r in rows:
            state_raw = r["state"]
            state = json.loads(state_raw) if isinstance(state_raw, str) else (state_raw or {})
            result.append(AgentState(
                agent_id=r["agent_id"],
                context_id=r["context_id"],
                state=state,
                updated_at=r["updated_at"],
            ))
        return result
