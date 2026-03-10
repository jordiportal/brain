"""
ConversationService — Orchestrates conversation persistence.

Central service that all routers call to save and retrieve conversation
messages. This makes Brain the source of truth for chat history,
independent of which client initiated the conversation.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Optional

from ..db.repositories.conversations import (
    ConversationRepository,
    Conversation,
    ConversationMessage,
)

logger = logging.getLogger(__name__)


class ConversationService:
    """
    High-level API for conversation persistence.

    Usage from routers:
        1. conv = await conversation_service.get_or_create(id, user_id, chain_id)
        2. await conversation_service.add_user_message(id, content)
        3. ... execute chain / stream ...
        4. await conversation_service.add_assistant_message(id, content, model, task_id, tokens)
    """

    def __init__(self):
        self._repo = ConversationRepository

    async def get_or_create(
        self,
        conversation_id: str,
        user_id: str,
        chain_id: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Conversation:
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        return await self._repo.get_or_create(
            conversation_id, user_id, chain_id=chain_id, model=model,
        )

    async def add_user_message(
        self,
        conversation_id: str,
        content: str,
        parts: Optional[list] = None,
        metadata: Optional[dict] = None,
    ) -> ConversationMessage:
        msg = ConversationMessage(
            conversation_id=conversation_id,
            role="user",
            content=content,
            parts=parts,
            metadata=metadata or {},
        )
        return await self._repo.add_message(msg)

    async def add_assistant_message(
        self,
        conversation_id: str,
        content: str,
        model: Optional[str] = None,
        task_id: Optional[str] = None,
        tokens_used: int = 0,
        parts: Optional[list] = None,
        metadata: Optional[dict] = None,
    ) -> ConversationMessage:
        msg = ConversationMessage(
            conversation_id=conversation_id,
            role="assistant",
            content=content,
            parts=parts,
            model=model,
            tokens_used=tokens_used,
            task_id=task_id,
            metadata=metadata or {},
        )
        return await self._repo.add_message(msg)

    async def add_system_message(
        self,
        conversation_id: str,
        content: str,
    ) -> ConversationMessage:
        msg = ConversationMessage(
            conversation_id=conversation_id,
            role="system",
            content=content,
        )
        return await self._repo.add_message(msg)

    async def get_recent_messages(
        self,
        conversation_id: str,
        max_messages: int = 20,
    ) -> list[ConversationMessage]:
        return await self._repo.get_recent_messages(conversation_id, max_messages)

    async def get_recent_as_llm_messages(
        self,
        conversation_id: str,
        max_messages: int = 20,
    ) -> list[dict]:
        """Get recent messages in LLM-compatible format [{role, content}]."""
        messages = await self.get_recent_messages(conversation_id, max_messages)
        result = []
        for m in messages:
            role = m.role
            if role == "agent":
                role = "assistant"
            result.append({"role": role, "content": m.content})
        return result

    async def get_history(
        self,
        conversation_id: str,
        limit: int = 100,
        before=None,
    ) -> list[ConversationMessage]:
        return await self._repo.get_messages(conversation_id, limit, before)

    async def list_conversations(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Conversation], int]:
        convs = await self._repo.list_by_user(user_id, limit, offset)
        total = await self._repo.count_by_user(user_id)
        return convs, total

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        return await self._repo.get(conversation_id)

    async def delete_conversation(self, conversation_id: str) -> bool:
        return await self._repo.delete(conversation_id)

    async def update_title(self, conversation_id: str, title: str):
        await self._repo.update_title(conversation_id, title)

    async def maybe_auto_title(
        self,
        conversation_id: str,
        user_message: str,
        llm_call=None,
    ):
        """
        Auto-generate a conversation title from the first user message.
        Only sets the title if it's currently None.
        """
        conv = await self._repo.get(conversation_id)
        if not conv or conv.title:
            return

        if llm_call:
            try:
                title = await llm_call(
                    f"Generate a very short title (max 6 words) for a conversation "
                    f"that starts with this message. Return ONLY the title, nothing else.\n\n"
                    f"Message: {user_message[:200]}"
                )
                title = title.strip().strip('"').strip("'")[:100]
                if title:
                    await self._repo.update_title(conversation_id, title)
                    return
            except Exception as e:
                logger.debug(f"Auto-title LLM call failed: {e}")

        title = user_message[:60].strip()
        if len(user_message) > 60:
            title += "..."
        await self._repo.update_title(conversation_id, title)

    async def count_messages(self, conversation_id: str) -> int:
        return await self._repo.count_messages(conversation_id)


# Global instance
conversation_service = ConversationService()
