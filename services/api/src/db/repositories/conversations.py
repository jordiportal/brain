"""
Conversation Repository — Persistence for chat conversations and messages.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

from ..connection import get_db

logger = logging.getLogger(__name__)


@dataclass
class Conversation:
    id: str = ""
    user_id: str = ""
    title: Optional[str] = None
    chain_id: Optional[str] = None
    model: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class ConversationMessage:
    id: str = ""
    conversation_id: str = ""
    role: str = "user"
    content: str = ""
    parts: Optional[list] = None
    model: Optional[str] = None
    tokens_used: int = 0
    task_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    created_at: Optional[datetime] = None


class ConversationRepository:
    """Repository for conversations and their messages."""

    # ---- Conversations ----

    @staticmethod
    async def get(conversation_id: str) -> Optional[Conversation]:
        db = get_db()
        row = await db.fetch_one(
            "SELECT * FROM conversations WHERE id = $1", conversation_id
        )
        if not row:
            return None
        return ConversationRepository._row_to_conversation(row)

    @staticmethod
    async def create(conv: Conversation) -> Conversation:
        db = get_db()
        if not conv.id:
            conv.id = str(uuid.uuid4())
        meta_json = json.dumps(conv.metadata, ensure_ascii=False, default=str)
        row = await db.fetch_one(
            """
            INSERT INTO conversations (id, user_id, title, chain_id, model, metadata)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING created_at, updated_at
            """,
            conv.id, conv.user_id, conv.title, conv.chain_id, conv.model, meta_json,
        )
        if row:
            conv.created_at = row["created_at"]
            conv.updated_at = row["updated_at"]
        return conv

    @staticmethod
    async def get_or_create(
        conversation_id: str,
        user_id: str,
        chain_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Conversation:
        existing = await ConversationRepository.get(conversation_id)
        if existing:
            return existing
        conv = Conversation(
            id=conversation_id, user_id=user_id,
            chain_id=chain_id, model=model,
        )
        return await ConversationRepository.create(conv)

    @staticmethod
    async def update_title(conversation_id: str, title: str):
        db = get_db()
        await db.execute(
            "UPDATE conversations SET title = $2, updated_at = NOW() WHERE id = $1",
            conversation_id, title,
        )

    @staticmethod
    async def touch(conversation_id: str):
        db = get_db()
        await db.execute(
            "UPDATE conversations SET updated_at = NOW() WHERE id = $1",
            conversation_id,
        )

    @staticmethod
    async def delete(conversation_id: str) -> bool:
        db = get_db()
        result = await db.execute(
            "DELETE FROM conversations WHERE id = $1", conversation_id
        )
        return result and "DELETE 1" in result

    @staticmethod
    async def list_by_user(
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        db = get_db()
        rows = await db.fetch_all(
            """
            SELECT * FROM conversations
            WHERE user_id = $1
            ORDER BY updated_at DESC
            LIMIT $2 OFFSET $3
            """,
            user_id, limit, offset,
        )
        return [ConversationRepository._row_to_conversation(r) for r in rows]

    @staticmethod
    async def count_by_user(user_id: str) -> int:
        db = get_db()
        row = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM conversations WHERE user_id = $1",
            user_id,
        )
        return row["cnt"] if row else 0

    # ---- Messages ----

    @staticmethod
    async def add_message(msg: ConversationMessage) -> ConversationMessage:
        db = get_db()
        if not msg.id:
            msg.id = str(uuid.uuid4())
        parts_json = json.dumps(msg.parts, ensure_ascii=False, default=str) if msg.parts else None
        meta_json = json.dumps(msg.metadata, ensure_ascii=False, default=str)
        row = await db.fetch_one(
            """
            INSERT INTO conversation_messages
                (id, conversation_id, role, content, parts, model, tokens_used, task_id, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING created_at
            """,
            msg.id, msg.conversation_id, msg.role, msg.content,
            parts_json, msg.model, msg.tokens_used, msg.task_id, meta_json,
        )
        if row:
            msg.created_at = row["created_at"]

        await ConversationRepository.touch(msg.conversation_id)
        return msg

    @staticmethod
    async def get_messages(
        conversation_id: str,
        limit: int = 100,
        before: Optional[datetime] = None,
    ) -> list[ConversationMessage]:
        db = get_db()
        if before:
            rows = await db.fetch_all(
                """
                SELECT * FROM conversation_messages
                WHERE conversation_id = $1 AND created_at < $2
                ORDER BY created_at ASC
                LIMIT $3
                """,
                conversation_id, before, limit,
            )
        else:
            rows = await db.fetch_all(
                """
                SELECT * FROM conversation_messages
                WHERE conversation_id = $1
                ORDER BY created_at ASC
                LIMIT $2
                """,
                conversation_id, limit,
            )
        return [ConversationRepository._row_to_message(r) for r in rows]

    @staticmethod
    async def get_recent_messages(
        conversation_id: str,
        max_messages: int = 20,
    ) -> list[ConversationMessage]:
        """Get the N most recent messages, returned in chronological order."""
        db = get_db()
        rows = await db.fetch_all(
            """
            SELECT * FROM (
                SELECT * FROM conversation_messages
                WHERE conversation_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            ) sub ORDER BY created_at ASC
            """,
            conversation_id, max_messages,
        )
        return [ConversationRepository._row_to_message(r) for r in rows]

    @staticmethod
    async def count_messages(conversation_id: str) -> int:
        db = get_db()
        row = await db.fetch_one(
            "SELECT COUNT(*) as cnt FROM conversation_messages WHERE conversation_id = $1",
            conversation_id,
        )
        return row["cnt"] if row else 0

    @staticmethod
    async def delete_message(message_id: str) -> bool:
        db = get_db()
        result = await db.execute(
            "DELETE FROM conversation_messages WHERE id = $1", message_id
        )
        return result and "DELETE 1" in result

    # ---- Helpers ----

    @staticmethod
    def _row_to_conversation(row) -> Conversation:
        meta_raw = row.get("metadata") or "{}"
        meta = json.loads(meta_raw) if isinstance(meta_raw, str) else (meta_raw or {})
        return Conversation(
            id=row["id"],
            user_id=row["user_id"],
            title=row.get("title"),
            chain_id=row.get("chain_id"),
            model=row.get("model"),
            metadata=meta,
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    @staticmethod
    def _row_to_message(row) -> ConversationMessage:
        parts_raw = row.get("parts")
        parts = json.loads(parts_raw) if isinstance(parts_raw, str) else parts_raw
        meta_raw = row.get("metadata") or "{}"
        meta = json.loads(meta_raw) if isinstance(meta_raw, str) else (meta_raw or {})
        return ConversationMessage(
            id=row["id"],
            conversation_id=row["conversation_id"],
            role=row["role"],
            content=row.get("content") or "",
            parts=parts,
            model=row.get("model"),
            tokens_used=row.get("tokens_used") or 0,
            task_id=row.get("task_id"),
            metadata=meta,
            created_at=row.get("created_at"),
        )
