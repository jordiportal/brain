"""
TaskManager — Orchestrates task lifecycle, state transitions, and persistence.

This is the central coordination point for the v2 engine. All task creation,
state changes, and queries go through here, ensuring consistent audit trails
and valid state transitions.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Optional

from .models import (
    Task,
    TaskState,
    TaskEvent,
    TaskFilters,
    Message,
    Part,
    Artifact,
    VALID_TRANSITIONS,
)
from ..db.repositories.tasks import TaskRepository

logger = logging.getLogger(__name__)


class InvalidTransitionError(Exception):
    """Raised when a task state transition is not allowed."""
    pass


class TaskManager:
    """
    Manages the full lifecycle of tasks.

    Responsibilities:
      - Create tasks from user input
      - Enforce valid state transitions
      - Record audit trail (task events)
      - Query and filter tasks
      - Track metrics (tokens, cost, duration)
    """

    def __init__(self):
        self._repo = TaskRepository

    async def create(
        self,
        input_message: Message,
        *,
        agent_id: Optional[str] = None,
        chain_id: Optional[str] = None,
        context_id: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Task:
        """Create a new task in SUBMITTED state."""
        task = Task(
            context_id=context_id or Task.__fields__["context_id"].default_factory(),
            parent_task_id=parent_task_id,
            agent_id=agent_id,
            chain_id=chain_id,
            state=TaskState.SUBMITTED,
            input=input_message,
            metadata=metadata or {},
            created_by=user_id,
        )

        await self._repo.create(task)
        await self._record_event(task, TaskState.SUBMITTED, "Task created")
        logger.info("Task created", task_id=task.id, agent_id=agent_id, chain_id=chain_id)
        return task

    async def create_from_text(
        self,
        text: str,
        *,
        role: str = "user",
        agent_id: Optional[str] = None,
        chain_id: Optional[str] = None,
        context_id: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Task:
        """Convenience: create task from a plain text input."""
        msg = Message.text(role, text)
        return await self.create(
            msg,
            agent_id=agent_id,
            chain_id=chain_id,
            context_id=context_id,
            parent_task_id=parent_task_id,
            user_id=user_id,
            metadata=metadata,
        )

    async def get(self, task_id: str) -> Optional[Task]:
        return await self._repo.get(task_id)

    async def list(self, filters: TaskFilters) -> list[Task]:
        return await self._repo.list_tasks(filters)

    async def count(self, filters: TaskFilters) -> int:
        return await self._repo.count(filters)

    async def transition(
        self,
        task_id: str,
        new_state: TaskState,
        reason: Optional[str] = None,
        output: Optional[Message] = None,
    ) -> Task:
        """
        Transition a task to a new state, enforcing valid transitions.

        Raises InvalidTransitionError if the transition is not allowed.
        """
        task = await self._repo.get(task_id)
        if not task:
            raise ValueError(f"Task not found: {task_id}")

        if not task.can_transition_to(new_state):
            raise InvalidTransitionError(
                f"Cannot transition task {task_id} from {task.state.value} to {new_state.value}"
            )

        updated = await self._repo.update_state(task_id, new_state, reason, output)
        await self._record_event(updated, new_state, reason, output)

        logger.info(
            "Task state changed",
            task_id=task_id,
            from_state=task.state.value,
            to_state=new_state.value,
            reason=reason,
        )
        return updated

    async def start(self, task_id: str) -> Task:
        """Move task from SUBMITTED to WORKING."""
        return await self.transition(task_id, TaskState.WORKING, "Execution started")

    async def complete(
        self,
        task_id: str,
        output: Optional[Message] = None,
        reason: Optional[str] = None,
    ) -> Task:
        """Move task to COMPLETED with optional output message."""
        return await self.transition(
            task_id, TaskState.COMPLETED, reason or "Task completed", output
        )

    async def fail(self, task_id: str, error: str) -> Task:
        """Move task to FAILED."""
        return await self.transition(task_id, TaskState.FAILED, error)

    async def cancel(self, task_id: str, reason: Optional[str] = None) -> Task:
        """Move task to CANCELED."""
        return await self.transition(
            task_id, TaskState.CANCELED, reason or "Canceled by user"
        )

    async def request_input(self, task_id: str, prompt: str) -> Task:
        """Move task to INPUT_REQUIRED with a prompt message."""
        prompt_msg = Message.text("agent", prompt)
        return await self.transition(
            task_id, TaskState.INPUT_REQUIRED, "Awaiting user input", prompt_msg
        )

    async def provide_input(self, task_id: str, input_message: Message) -> Task:
        """
        Resume a task that is waiting for input.
        Adds the input to history and transitions back to WORKING.
        """
        await self._repo.add_message(task_id, input_message)
        return await self.transition(task_id, TaskState.WORKING, "User provided input")

    async def retry(self, task_id: str) -> Task:
        """Retry a FAILED task from its last checkpoint."""
        return await self.transition(task_id, TaskState.WORKING, "Retrying from checkpoint")

    async def add_message(self, task_id: str, message: Message):
        """Add a message to the task history."""
        await self._repo.add_message(task_id, message)

    async def add_artifact(self, task_id: str, artifact: Artifact):
        """Add an artifact to the task."""
        await self._repo.add_artifact(task_id, artifact)

    async def update_metrics(
        self,
        task_id: str,
        tokens_used: Optional[int] = None,
        cost_usd: Optional[float] = None,
        duration_ms: Optional[int] = None,
        iterations: Optional[int] = None,
    ):
        """Update task metrics (tokens, cost, duration, iterations)."""
        await self._repo.update_metrics(
            task_id,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
            iterations=iterations,
        )

    async def set_checkpoint(self, task_id: str, thread_id: str):
        """Set the LangGraph checkpoint thread ID for a task."""
        await self._repo.set_checkpoint(task_id, thread_id)

    async def get_events(self, task_id: str) -> list[TaskEvent]:
        """Get the audit trail for a task."""
        return await self._repo.get_events(task_id)

    async def get_by_context(self, context_id: str) -> list[Task]:
        """Get all tasks in a conversation context."""
        return await self._repo.list_tasks(
            TaskFilters(context_id=context_id, limit=100)
        )

    async def get_children(self, task_id: str) -> list[Task]:
        """Get child tasks (delegations)."""
        return await self._repo.list_tasks(
            TaskFilters(parent_task_id=task_id, limit=100)
        )

    async def cleanup_old(self, days: int = 30) -> int:
        """Delete old completed/failed/canceled tasks."""
        count = await self._repo.cleanup_old(days)
        if count > 0:
            logger.info(f"Cleaned up {count} old tasks")
        return count

    async def _record_event(
        self,
        task: Task,
        state: TaskState,
        reason: Optional[str] = None,
        message: Optional[Message] = None,
    ):
        """Record a state transition in the audit trail."""
        event = TaskEvent(
            task_id=task.id,
            state=state,
            reason=reason,
            message=message,
        )
        await self._repo.create_event(event)


# Global instance
task_manager = TaskManager()
