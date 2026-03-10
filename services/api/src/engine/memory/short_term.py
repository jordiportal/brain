"""
Short-term memory — Current session messages.

Backed by LangGraph checkpoint state or task history.
"""

import logging
from typing import Optional

from ..models import Task, Message

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """
    Session-scoped memory from the current task's history
    and LangGraph checkpoint state.
    """

    async def get(self, task: Optional[Task] = None, context_id: Optional[str] = None) -> list[Message]:
        """
        Get recent messages from the current session.

        Priority:
          1. Task history (if task provided)
          2. Legacy memory store (fallback for backward compat)
        """
        if task and task.history:
            return task.history

        if context_id:
            from ..executor import chain_executor
            legacy_memory = chain_executor.get_memory(context_id)
            return [
                Message.text(m.get("role", "user"), m.get("content", ""))
                for m in legacy_memory
            ]

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
