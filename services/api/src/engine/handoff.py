"""
HandoffManager — Structured delegation between agents with context filtering.

Improves on the existing delegate/parallel_delegate pattern by:
  - Creating child Tasks for each delegation (visible and queryable)
  - Filtering context before passing to child agents
  - Supporting parallel delegations with independent child tasks
  - Providing structured results (Message + Artifact[]) instead of raw strings
"""

import asyncio
import logging
from typing import Optional
from dataclasses import dataclass, field
from pydantic import BaseModel

from .models import Task, TaskState, Message, Part, Artifact
from .task_manager import TaskManager, task_manager

logger = logging.getLogger(__name__)


class ContextFilter(BaseModel):
    """Controls what context is passed to a delegated agent."""
    include_history: bool = True
    max_messages: Optional[int] = None
    include_artifacts: bool = False
    include_agent_state: bool = False
    custom_context: Optional[str] = None
    include_roles: Optional[list[str]] = None  # e.g. ["user", "agent"]


class DelegationRequest(BaseModel):
    """A request to delegate work to an agent."""
    agent_id: str
    instruction: str
    context_filter: ContextFilter = ContextFilter()
    metadata: Optional[dict] = None


@dataclass
class DelegationResult:
    """Result of a delegation."""
    task: Task
    response_text: str = ""
    artifacts: list[Artifact] = field(default_factory=list)
    success: bool = False


class HandoffManager:
    """
    Manages structured delegations between agents.

    Each delegation creates a child Task, filters the parent's context
    according to the ContextFilter, and returns structured results.
    """

    def __init__(self, tm: Optional[TaskManager] = None):
        self._task_manager = tm or task_manager

    def filter_context(
        self,
        parent_task: Task,
        context_filter: ContextFilter,
    ) -> list[Message]:
        """
        Filter the parent task's history according to the context filter.

        Returns a list of Messages to include in the child task's context.
        """
        if not context_filter.include_history:
            return []

        messages = list(parent_task.history)

        if context_filter.include_roles:
            messages = [m for m in messages if m.role in context_filter.include_roles]

        if context_filter.max_messages and len(messages) > context_filter.max_messages:
            messages = messages[-context_filter.max_messages:]

        return messages

    async def delegate(
        self,
        from_task: Task,
        to_agent_id: str,
        instruction: str,
        context_filter: Optional[ContextFilter] = None,
        metadata: Optional[dict] = None,
    ) -> DelegationResult:
        """
        Delegate work to another agent by creating a child task.

        Args:
            from_task: The parent task initiating the delegation
            to_agent_id: Agent to delegate to
            instruction: What the agent should do
            context_filter: Controls what context to pass
            metadata: Optional metadata for the child task

        Returns:
            DelegationResult with the child task and response
        """
        cf = context_filter or ContextFilter()

        # Filter context from parent
        filtered_history = self.filter_context(from_task, cf)

        # Build child input
        parts = [Part(type="text", text=instruction)]
        if cf.custom_context:
            parts.append(Part(type="text", text=f"\n\nAdditional context:\n{cf.custom_context}"))

        input_msg = Message(
            role="user",
            parts=parts,
            metadata={"delegated_from": from_task.id},
        )

        # Create child task
        child_task = await self._task_manager.create(
            input_msg,
            agent_id=to_agent_id,
            context_id=from_task.context_id,
            parent_task_id=from_task.id,
            user_id=from_task.created_by,
            metadata={
                **(metadata or {}),
                "delegation": True,
                "parent_task_id": from_task.id,
                "filtered_history_count": len(filtered_history),
            },
        )

        # Add filtered history to child task
        for msg in filtered_history:
            await self._task_manager.add_message(child_task.id, msg)

        logger.info(
            f"Delegated to {to_agent_id}",
            parent_task=from_task.id,
            child_task=child_task.id,
            instruction=instruction[:80],
        )

        return DelegationResult(
            task=child_task,
            success=True,
        )

    async def parallel_delegate(
        self,
        from_task: Task,
        delegations: list[DelegationRequest],
    ) -> list[DelegationResult]:
        """
        Execute multiple delegations in parallel, each as a child task.

        All child tasks share the same parent and context_id.
        """
        async def _do_delegation(req: DelegationRequest) -> DelegationResult:
            return await self.delegate(
                from_task=from_task,
                to_agent_id=req.agent_id,
                instruction=req.instruction,
                context_filter=req.context_filter,
                metadata=req.metadata,
            )

        results = await asyncio.gather(
            *[_do_delegation(d) for d in delegations],
            return_exceptions=True,
        )

        final = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Delegation {i} failed: {result}")
                final.append(DelegationResult(
                    task=Task(
                        context_id=from_task.context_id,
                        input=Message.text("user", delegations[i].instruction),
                        state=TaskState.FAILED,
                        state_reason=str(result),
                    ),
                    success=False,
                ))
            else:
                final.append(result)

        return final

    async def get_delegation_tree(self, task_id: str) -> dict:
        """
        Get the full delegation tree for a task.

        Returns a nested dict with task info and children.
        """
        task = await self._task_manager.get(task_id)
        if not task:
            return {}

        children = await self._task_manager.get_children(task_id)
        child_trees = []
        for child in children:
            child_trees.append(await self.get_delegation_tree(child.id))

        return {
            "id": task.id,
            "agent_id": task.agent_id,
            "state": task.state.value,
            "input": task.input.text_content[:100] if task.input else "",
            "output": task.output.text_content[:100] if task.output else "",
            "children": child_trees,
        }


# Global instance
handoff_manager = HandoffManager()
