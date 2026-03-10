"""
Short-term memory — Current session messages.

Primary source is now conversation_messages in PostgreSQL.
Falls back to task history or legacy in-memory store.
"""

import logging
from typing import Optional

from ..models import Task, Message

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """
    Session-scoped memory. Reads from conversation_messages (DB)
    first, with fallback to task history or legacy memory store.
    """

    async def get(
        self,
        task: Optional[Task] = None,
        context_id: Optional[str] = None,
        max_messages: int = 20,
    ) -> list[Message]:
        # Try DB-backed conversation messages first
        if context_id:
            try:
                from ..conversation_service import conversation_service
                db_msgs = await conversation_service.get_recent_messages(
                    context_id, max_messages=max_messages,
                )
                if db_msgs:
                    return [
                        Message.text(m.role if m.role != "agent" else "assistant", m.content)
                        for m in db_msgs
                    ]
            except Exception as e:
                logger.debug(f"Short-term DB fallback: {e}")

        if task and task.history:
            return task.history

        if context_id:
            try:
                from ..executor import chain_executor
                legacy_memory = chain_executor.get_memory(context_id)
                return [
                    Message.text(m.get("role", "user"), m.get("content", ""))
                    for m in legacy_memory
                ]
            except Exception:
                pass

        return []

    def to_llm_messages(self, messages: list[Message], max_messages: int = 20) -> list[dict]:
        """Convert Messages to LLM-compatible dicts."""
        result = []
        for msg in messages[-max_messages:]:
            role = msg.role
            if role == "agent":
                role = "assistant"
            result.append({
                "role": role,
                "content": msg.text_content,
            })
        return result
