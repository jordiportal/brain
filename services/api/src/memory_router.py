"""
REST API for memory management.

Endpoints:
  GET    /api/v1/memory/context         — Get facts and episodes for a user
  POST   /api/v1/memory/facts           — Create a new fact manually
  PUT    /api/v1/memory/facts/{id}      — Update a fact
  DELETE /api/v1/memory/facts/{id}      — Delete a fact
  PUT    /api/v1/memory/episodes/{id}   — Update an episode
  DELETE /api/v1/memory/episodes/{id}   — Delete an episode
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query as QueryParam
from pydantic import BaseModel

from src.auth.dependencies import optional_current_user
from src.db.repositories.memory import MemoryRepository, MemoryFact

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


class CreateFactRequest(BaseModel):
    content: str
    type: str = "fact"
    agent_id: Optional[str] = None
    user_id: Optional[str] = None


class UpdateFactRequest(BaseModel):
    content: str
    type: Optional[str] = None


class UpdateEpisodeRequest(BaseModel):
    summary: str
    key_points: Optional[list] = None


def _resolve_user(user_id: Optional[str], current_user: Optional[dict]) -> str:
    uid = user_id
    if not uid and current_user:
        uid = current_user.get("email", "anonymous")
    return uid or "anonymous"


@router.get("/context")
async def get_memory_context(
    user_id: Optional[str] = QueryParam(None),
    agent_id: Optional[str] = QueryParam(None),
    limit: int = QueryParam(20, ge=1, le=100),
    current_user: Optional[dict] = Depends(optional_current_user),
) -> MemoryContextResponse:
    uid = _resolve_user(user_id, current_user)

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


@router.post("/facts")
async def create_fact(
    request: CreateFactRequest,
    current_user: Optional[dict] = Depends(optional_current_user),
):
    uid = _resolve_user(request.user_id, current_user)
    fact = MemoryFact(
        user_id=uid,
        content=request.content,
        type=request.type,
        agent_id=request.agent_id,
    )
    created = await MemoryRepository.add_fact(fact)
    return {
        "id": created.id,
        "content": created.content,
        "type": created.type,
        "created_at": created.created_at.isoformat() if created.created_at else None,
    }


@router.put("/facts/{fact_id}")
async def update_fact(
    fact_id: int,
    request: UpdateFactRequest,
):
    ok = await MemoryRepository.update_fact(fact_id, request.content, request.type)
    if not ok:
        raise HTTPException(status_code=404, detail="Fact not found")
    return {"status": "ok", "id": fact_id}


@router.delete("/facts/{fact_id}")
async def delete_fact(fact_id: int):
    ok = await MemoryRepository.delete_fact(fact_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Fact not found")
    return {"status": "ok", "id": fact_id}


@router.put("/episodes/{episode_id}")
async def update_episode(
    episode_id: int,
    request: UpdateEpisodeRequest,
):
    ok = await MemoryRepository.update_episode(episode_id, request.summary, request.key_points)
    if not ok:
        raise HTTPException(status_code=404, detail="Episode not found")
    return {"status": "ok", "id": episode_id}


@router.delete("/episodes/{episode_id}")
async def delete_episode(episode_id: int):
    ok = await MemoryRepository.delete_episode(episode_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Episode not found")
    return {"status": "ok", "id": episode_id}
