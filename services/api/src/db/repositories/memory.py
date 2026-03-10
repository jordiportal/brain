"""
Memory Repository — Persistence for long-term facts and episodic summaries.
"""

import json
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

from ..connection import get_db

logger = logging.getLogger(__name__)


@dataclass
class MemoryFact:
    id: Optional[int] = None
    agent_id: Optional[str] = None
    user_id: str = ""
    type: str = "fact"  # fact, preference, knowledge, correction
    content: str = ""
    source_task_id: Optional[str] = None
    relevance_score: float = 1.0
    created_at: Optional[datetime] = None
    accessed_at: Optional[datetime] = None


@dataclass
class MemoryEpisode:
    id: Optional[int] = None
    agent_id: Optional[str] = None
    user_id: str = ""
    context_id: Optional[str] = None
    summary: str = ""
    key_points: list = field(default_factory=list)
    task_ids: list = field(default_factory=list)
    message_count: int = 0
    created_at: Optional[datetime] = None


class MemoryRepository:
    """Repository for long-term memory and episodic summaries."""

    # ---- Long-term facts ----

    @staticmethod
    async def add_fact(fact: MemoryFact) -> MemoryFact:
        db = get_db()
        row = await db.fetch_one(
            """
            INSERT INTO memory_long_term (agent_id, user_id, type, content, source_task_id, relevance_score)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, created_at
            """,
            fact.agent_id, fact.user_id, fact.type, fact.content,
            fact.source_task_id, fact.relevance_score,
        )
        if row:
            fact.id = row["id"]
            fact.created_at = row["created_at"]
        return fact

    @staticmethod
    async def search_facts(
        user_id: str,
        agent_id: Optional[str] = None,
        limit: int = 10,
    ) -> list[MemoryFact]:
        """
        Search for relevant facts. Currently a simple recency-based query.
        Vector similarity search will be added when embeddings are populated.
        """
        db = get_db()
        if agent_id:
            rows = await db.fetch_all(
                """
                SELECT * FROM memory_long_term
                WHERE user_id = $1 AND (agent_id = $2 OR agent_id IS NULL)
                ORDER BY relevance_score DESC, accessed_at DESC
                LIMIT $3
                """,
                user_id, agent_id, limit,
            )
        else:
            rows = await db.fetch_all(
                """
                SELECT * FROM memory_long_term
                WHERE user_id = $1
                ORDER BY relevance_score DESC, accessed_at DESC
                LIMIT $2
                """,
                user_id, limit,
            )

        result = []
        for r in rows:
            result.append(MemoryFact(
                id=r["id"], agent_id=r["agent_id"], user_id=r["user_id"],
                type=r["type"], content=r["content"],
                source_task_id=r.get("source_task_id"),
                relevance_score=float(r["relevance_score"] or 1.0),
                created_at=r["created_at"], accessed_at=r["accessed_at"],
            ))
        return result

    @staticmethod
    async def search_facts_by_embedding(
        user_id: str,
        embedding: list[float],
        agent_id: Optional[str] = None,
        limit: int = 10,
    ) -> list[MemoryFact]:
        """Semantic search using pgvector cosine similarity."""
        db = get_db()
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        if agent_id:
            rows = await db.fetch_all(
                """
                SELECT *, (embedding <=> $3::vector) as distance
                FROM memory_long_term
                WHERE user_id = $1 AND (agent_id = $2 OR agent_id IS NULL)
                  AND embedding IS NOT NULL
                ORDER BY distance ASC
                LIMIT $4
                """,
                user_id, agent_id, embedding_str, limit,
            )
        else:
            rows = await db.fetch_all(
                """
                SELECT *, (embedding <=> $2::vector) as distance
                FROM memory_long_term
                WHERE user_id = $1 AND embedding IS NOT NULL
                ORDER BY distance ASC
                LIMIT $3
                """,
                user_id, embedding_str, limit,
            )

        result = []
        for r in rows:
            result.append(MemoryFact(
                id=r["id"], agent_id=r["agent_id"], user_id=r["user_id"],
                type=r["type"], content=r["content"],
                source_task_id=r.get("source_task_id"),
                relevance_score=float(r["relevance_score"] or 1.0),
                created_at=r["created_at"], accessed_at=r["accessed_at"],
            ))
        return result

    @staticmethod
    async def touch_fact(fact_id: int):
        """Update accessed_at timestamp for a fact."""
        db = get_db()
        await db.execute(
            "UPDATE memory_long_term SET accessed_at = NOW() WHERE id = $1",
            fact_id,
        )

    @staticmethod
    async def delete_fact(fact_id: int) -> bool:
        db = get_db()
        result = await db.execute(
            "DELETE FROM memory_long_term WHERE id = $1", fact_id,
        )
        return result and "DELETE 1" in result

    @staticmethod
    async def count_facts(user_id: str, agent_id: Optional[str] = None) -> int:
        db = get_db()
        if agent_id:
            row = await db.fetch_one(
                "SELECT COUNT(*) as cnt FROM memory_long_term WHERE user_id = $1 AND agent_id = $2",
                user_id, agent_id,
            )
        else:
            row = await db.fetch_one(
                "SELECT COUNT(*) as cnt FROM memory_long_term WHERE user_id = $1",
                user_id,
            )
        return row["cnt"] if row else 0

    # ---- Episodic summaries ----

    @staticmethod
    async def add_episode(episode: MemoryEpisode) -> MemoryEpisode:
        db = get_db()
        row = await db.fetch_one(
            """
            INSERT INTO memory_episodes (agent_id, user_id, context_id, summary, key_points, task_ids, message_count)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id, created_at
            """,
            episode.agent_id, episode.user_id, episode.context_id,
            episode.summary,
            json.dumps(episode.key_points, ensure_ascii=False),
            episode.task_ids,
            episode.message_count,
        )
        if row:
            episode.id = row["id"]
            episode.created_at = row["created_at"]
        return episode

    @staticmethod
    async def get_recent_episodes(
        user_id: str,
        agent_id: Optional[str] = None,
        limit: int = 5,
    ) -> list[MemoryEpisode]:
        db = get_db()
        if agent_id:
            rows = await db.fetch_all(
                """
                SELECT * FROM memory_episodes
                WHERE user_id = $1 AND (agent_id = $2 OR agent_id IS NULL)
                ORDER BY created_at DESC
                LIMIT $3
                """,
                user_id, agent_id, limit,
            )
        else:
            rows = await db.fetch_all(
                """
                SELECT * FROM memory_episodes
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                user_id, limit,
            )

        result = []
        for r in rows:
            kp_raw = r["key_points"]
            kp = json.loads(kp_raw) if isinstance(kp_raw, str) else (kp_raw or [])
            result.append(MemoryEpisode(
                id=r["id"], agent_id=r["agent_id"], user_id=r["user_id"],
                context_id=r["context_id"], summary=r["summary"],
                key_points=kp, task_ids=list(r["task_ids"] or []),
                message_count=r["message_count"] or 0,
                created_at=r["created_at"],
            ))
        return result

    @staticmethod
    async def count_episodes(user_id: str, agent_id: Optional[str] = None) -> int:
        db = get_db()
        if agent_id:
            row = await db.fetch_one(
                "SELECT COUNT(*) as cnt FROM memory_episodes WHERE user_id = $1 AND agent_id = $2",
                user_id, agent_id,
            )
        else:
            row = await db.fetch_one(
                "SELECT COUNT(*) as cnt FROM memory_episodes WHERE user_id = $1",
                user_id,
            )
        return row["cnt"] if row else 0
