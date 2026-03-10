"""
Long-term memory — Cross-session facts with vector embeddings.

Stores extracted facts, user preferences, corrections, and domain knowledge.
Uses pgvector for semantic similarity search.
"""

import logging
from typing import Optional

from ...db.repositories.memory import MemoryRepository, MemoryFact
from ..models import Task

logger = logging.getLogger(__name__)


class LongTermMemory:
    """
    Cross-session factual memory backed by PostgreSQL + pgvector.
    """

    def __init__(self):
        self._repo = MemoryRepository

    async def search(
        self,
        user_id: str,
        agent_id: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 10,
    ) -> list[MemoryFact]:
        """
        Search for relevant facts.

        If query is provided and embeddings are available, uses semantic search.
        Otherwise falls back to recency-based retrieval.
        """
        # TODO: generate embedding from query and use search_facts_by_embedding
        return await self._repo.search_facts(user_id, agent_id, limit)

    async def add_fact(
        self,
        user_id: str,
        content: str,
        fact_type: str = "fact",
        agent_id: Optional[str] = None,
        source_task_id: Optional[str] = None,
    ) -> MemoryFact:
        """Store a new fact in long-term memory."""
        fact = MemoryFact(
            agent_id=agent_id,
            user_id=user_id,
            type=fact_type,
            content=content,
            source_task_id=source_task_id,
        )
        return await self._repo.add_fact(fact)

    async def extract_facts(self, task: Task, llm_call=None):
        """
        Extract facts from a completed task using LLM.

        Analyzes the task history and output to identify:
        - User preferences (likes, dislikes, settings)
        - Factual corrections (the user corrected a mistake)
        - Domain knowledge (facts learned during the task)
        """
        if not task.created_by or not task.history:
            return []

        if not llm_call:
            logger.debug("No LLM call provided for fact extraction — skipping")
            return []

        conversation = "\n".join(
            f"{m.role}: {m.text_content}" for m in task.history[:20]
        )

        extraction_prompt = f"""Analyze this conversation and extract important facts about the user.
Focus on: preferences, corrections, domain knowledge, and personal information they shared.
Return each fact as a separate line. If there are no meaningful facts, return "NONE".

Conversation:
{conversation}

Extracted facts (one per line):"""

        try:
            response = await llm_call(extraction_prompt)
            if not response or "NONE" in response.upper():
                return []

            facts = []
            for line in response.strip().split("\n"):
                line = line.strip().lstrip("- •")
                if line and len(line) > 5:
                    fact = await self.add_fact(
                        user_id=task.created_by,
                        content=line,
                        fact_type="fact",
                        agent_id=task.agent_id,
                        source_task_id=task.id,
                    )
                    facts.append(fact)

            logger.info(f"Extracted {len(facts)} facts from task {task.id}")
            return facts
        except Exception as e:
            logger.warning(f"Fact extraction failed: {e}")
            return []

    def format_for_prompt(self, facts: list[MemoryFact]) -> str:
        """Format facts for injection into a system prompt."""
        if not facts:
            return ""

        lines = ["## Known facts about the user:"]
        for f in facts:
            lines.append(f"- [{f.type}] {f.content}")
        return "\n".join(lines)
