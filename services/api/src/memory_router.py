"""
REST API for memory context retrieval.

Endpoint:
  GET /api/v1/memory/context — Get facts and episodes for a user
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query as QueryParam
from pydantic import BaseModel

from src.auth.dependencies import optional_current_user
from src.db.repositories.memory import MemoryRepository

router = APIRouter(prefix="/memory", tags=["Memory"])


class FactItem(BaseModel):
    id: int
    type: str
    content: str
    agent_id: Optional[str] = None
    relevance_score: float = 1.0
    created_at: Optional[str] = None


class EpisodeItem(BaseModel):
    id: int
    summary: str
    key_points: list = []
    message_count: int = 0
    created_at: Optional[str] = None


class MemoryContextResponse(BaseModel):
    facts: list[FactItem] = []
    episodes: list[EpisodeItem] = []
    facts_count: int = 0
    episodes_count: int = 0


@router.get("/context")
async def get_memory_context(
    user_id: Optional[str] = QueryParam(None),
    agent_id: Optional[str] = QueryParam(None),
    limit: int = QueryParam(20, ge=1, le=100),
    current_user: Optional[dict] = Depends(optional_current_user),
) -> MemoryContextResponse:
    uid = user_id
    if not uid and current_user:
        uid = current_user.get("email", "anonymous")
    if not uid:
        uid = "anonymous"

    facts_raw = await MemoryRepository.search_facts(uid, agent_id, limit)
    episodes_raw = await MemoryRepository.get_recent_episodes(uid, agent_id, limit)
    facts_count = await MemoryRepository.count_facts(uid, agent_id)
    episodes_count = await MemoryRepository.count_episodes(uid, agent_id)

    facts = [
        FactItem(
            id=f.id or 0,
            type=f.type,
            content=f.content,
            agent_id=f.agent_id,
            relevance_score=f.relevance_score,
            created_at=f.created_at.isoformat() if f.created_at else None,
        )
        for f in facts_raw
    ]

    episodes = [
        EpisodeItem(
            id=e.id or 0,
            summary=e.summary,
            key_points=e.key_points,
            message_count=e.message_count,
            created_at=e.created_at.isoformat() if e.created_at else None,
        )
        for e in episodes_raw
    ]

    return MemoryContextResponse(
        facts=facts,
        episodes=episodes,
        facts_count=facts_count,
        episodes_count=episodes_count,
    )
