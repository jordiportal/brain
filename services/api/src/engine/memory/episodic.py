"""
Episodic memory — Auto-generated summaries of past interactions.

Provides historical context by summarizing completed tasks into
concise episodes. Helps agents maintain continuity across sessions.
"""

import logging
from typing import Optional

from ...db.repositories.memory import MemoryRepository, MemoryEpisode
from ..models import Task

logger = logging.getLogger(__name__)

EPISODE_THRESHOLD = 5  # min messages before creating an episode


class EpisodicMemory:
    """
    Auto-summarized interaction episodes backed by PostgreSQL.
    """

    def __init__(self):
        self._repo = MemoryRepository

    async def get_recent(
        self,
        user_id: str,
        agent_id: Optional[str] = None,
        limit: int = 5,
    ) -> list[MemoryEpisode]:
        """Get the N most recent episodes for context."""
        return await self._repo.get_recent_episodes(user_id, agent_id, limit)

    async def maybe_summarize(self, task: Task, llm_call=None) -> Optional[MemoryEpisode]:
        """
        Create an episodic summary if the task has enough history.

        Only summarizes tasks with at least EPISODE_THRESHOLD messages.
        """
        if not task.created_by:
            return None

        msg_count = len(task.history)
        if msg_count < EPISODE_THRESHOLD:
            return None

        if not llm_call:
            # Without LLM, create a basic episode from available data
            summary = f"Task {task.id}: "
            if task.output:
                summary += task.output.text_content[:200]
            elif task.state_reason:
                summary += task.state_reason

            episode = MemoryEpisode(
                agent_id=task.agent_id,
                user_id=task.created_by,
                context_id=task.context_id,
                summary=summary,
                key_points=[],
                task_ids=[task.id],
                message_count=msg_count,
            )
            return await self._repo.add_episode(episode)

        conversation = "\n".join(
            f"{m.role}: {m.text_content[:100]}" for m in task.history[:30]
        )

        summary_prompt = f"""Summarize this conversation in 2-3 sentences.
Also extract 3-5 key points as a bullet list.

Conversation:
{conversation}

Summary:"""

        try:
            response = await llm_call(summary_prompt)
            if not response:
                return None

            lines = response.strip().split("\n")
            summary_lines = []
            key_points = []
            in_key_points = False

            for line in lines:
                stripped = line.strip()
                if stripped.startswith("- ") or stripped.startswith("• "):
                    in_key_points = True
                    key_points.append(stripped.lstrip("- •").strip())
                elif not in_key_points:
                    summary_lines.append(stripped)

            summary = " ".join(summary_lines).strip()
            if not summary:
                summary = response[:200]

            episode = MemoryEpisode(
                agent_id=task.agent_id,
                user_id=task.created_by,
                context_id=task.context_id,
                summary=summary,
                key_points=key_points,
                task_ids=[task.id],
                message_count=msg_count,
            )
            result = await self._repo.add_episode(episode)
            logger.info(f"Created episode from task {task.id}: {summary[:80]}")
            return result

        except Exception as e:
            logger.warning(f"Episode summarization failed: {e}")
            return None

    def format_for_prompt(self, episodes: list[MemoryEpisode]) -> str:
        """Format episodes for injection into a system prompt."""
        if not episodes:
            return ""

        lines = ["## Previous interaction summaries:"]
        for ep in episodes:
            lines.append(f"- {ep.summary}")
            if ep.key_points:
                for kp in ep.key_points[:3]:
                    lines.append(f"  • {kp}")
        return "\n".join(lines)
