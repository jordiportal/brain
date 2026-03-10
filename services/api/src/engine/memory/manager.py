"""
MemoryManager — Orchestrates the three-layer memory system.

Assembles context from short-term, long-term, and episodic memory
before each agent execution, and saves interactions after completion.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable

from ..models import Task, Message
from .short_term import ShortTermMemory
from .long_term import LongTermMemory
from .episodic import EpisodicMemory
from ...db.repositories.memory import MemoryFact, MemoryEpisode

logger = logging.getLogger(__name__)


@dataclass
class MemoryContext:
    """Assembled memory context from all three layers."""
    short_term: list[Message] = field(default_factory=list)
    long_term: list[MemoryFact] = field(default_factory=list)
    episodes: list[MemoryEpisode] = field(default_factory=list)

    def to_system_addendum(self) -> str:
        """Generate text to append to the system prompt."""
        parts = []

        long_term_mgr = LongTermMemory()
        lt_text = long_term_mgr.format_for_prompt(self.long_term)
        if lt_text:
            parts.append(lt_text)

        episodic_mgr = EpisodicMemory()
        ep_text = episodic_mgr.format_for_prompt(self.episodes)
        if ep_text:
            parts.append(ep_text)

        return "\n\n".join(parts)

    def to_llm_messages(self, max_messages: int = 20) -> list[dict]:
        """Convert short-term messages to LLM format."""
        stm = ShortTermMemory()
        return stm.to_llm_messages(self.short_term, max_messages)


class MemoryManager:
    """
    Orchestrates memory retrieval and storage across all layers.

    Usage:
      1. Before execution: ctx = await mm.get_context(...)
      2. After completion: await mm.save_interaction(task)
    """

    def __init__(self):
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
        self.episodic = EpisodicMemory()

    async def get_context(
        self,
        user_id: str,
        agent_id: Optional[str] = None,
        context_id: Optional[str] = None,
        task: Optional[Task] = None,
        query: Optional[str] = None,
    ) -> MemoryContext:
        """
        Assemble memory context from all three layers.

        Args:
            user_id: Current user
            agent_id: Agent being executed
            context_id: Conversation/session ID
            task: Current task (for short-term)
            query: User's query (for semantic search in long-term)
        """
        short = await self.short_term.get(task=task, context_id=context_id)

        long = []
        try:
            long = await self.long_term.search(user_id, agent_id, query)
        except Exception as e:
            logger.warning(f"Long-term memory search failed: {e}")

        episodes = []
        try:
            episodes = await self.episodic.get_recent(user_id, agent_id)
        except Exception as e:
            logger.warning(f"Episodic memory retrieval failed: {e}")

        return MemoryContext(
            short_term=short,
            long_term=long,
            episodes=episodes,
        )

    async def save_interaction(
        self,
        task: Task,
        llm_call: Optional[Callable[[str], Awaitable[str]]] = None,
    ):
        """
        Post-completion: extract facts and create episodic summaries.

        Args:
            task: The completed task
            llm_call: Optional async function to call LLM for extraction/summarization
        """
        if not task.created_by:
            return

        try:
            await self.long_term.extract_facts(task, llm_call)
        except Exception as e:
            logger.warning(f"Fact extraction failed for task {task.id}: {e}")

        try:
            await self.episodic.maybe_summarize(task, llm_call)
        except Exception as e:
            logger.warning(f"Episode summarization failed for task {task.id}: {e}")


# Global instance
memory_manager = MemoryManager()
