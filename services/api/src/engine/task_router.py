"""
Task Router — REST endpoints for engine v2 tasks.

Provides CRUD operations, state transitions, and event history
for the task-centric execution model.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .models import Task, TaskState, TaskFilters, Message, Part, TaskEvent
from .task_manager import task_manager, InvalidTransitionError

router = APIRouter(prefix="/engine/tasks", tags=["Engine Tasks"])


# ---- Request/Response schemas ----

class TaskCreateRequest(BaseModel):
    message: str
    agent_id: Optional[str] = None
    chain_id: Optional[str] = None
    context_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    metadata: Optional[dict] = None


class TaskResumeRequest(BaseModel):
    message: str
    metadata: Optional[dict] = None


class TaskListResponse(BaseModel):
    tasks: list[Task]
    total: int
    limit: int
    offset: int


class TaskEventListResponse(BaseModel):
    events: list[TaskEvent]


# ---- Endpoints ----

@router.post("", response_model=Task)
async def create_task(request: TaskCreateRequest):
    """Create a new task in SUBMITTED state."""
    task = await task_manager.create_from_text(
        request.message,
        agent_id=request.agent_id,
        chain_id=request.chain_id,
        context_id=request.context_id,
        parent_task_id=request.parent_task_id,
        metadata=request.metadata,
    )
    return task


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    context_id: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    chain_id: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    created_by: Optional[str] = Query(None),
    parent_task_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    order_by: str = Query("created_at"),
    order_dir: str = Query("DESC"),
):
    """List tasks with filtering and pagination."""
    task_state = TaskState(state) if state else None

    filters = TaskFilters(
        context_id=context_id,
        agent_id=agent_id,
        chain_id=chain_id,
        parent_task_id=parent_task_id,
        state=task_state,
        created_by=created_by,
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_dir=order_dir,
    )
    tasks = await task_manager.list(filters)
    total = await task_manager.count(filters)
    return TaskListResponse(tasks=tasks, total=total, limit=limit, offset=offset)


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str):
    """Get a task by ID."""
    task = await task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/{task_id}/cancel", response_model=Task)
async def cancel_task(task_id: str, reason: Optional[str] = Query(None)):
    """Cancel a running or waiting task."""
    try:
        return await task_manager.cancel(task_id, reason)
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{task_id}/resume", response_model=Task)
async def resume_task(task_id: str, request: TaskResumeRequest):
    """
    Resume a task that is in INPUT_REQUIRED or FAILED state.

    For INPUT_REQUIRED: provides user input and continues execution.
    For FAILED: retries from the last checkpoint.
    """
    task = await task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        if task.state == TaskState.INPUT_REQUIRED:
            input_msg = Message.text("user", request.message)
            return await task_manager.provide_input(task_id, input_msg)
        elif task.state == TaskState.FAILED:
            return await task_manager.retry(task_id)
        else:
            raise HTTPException(
                status_code=409,
                detail=f"Task is in {task.state.value} state and cannot be resumed",
            )
    except InvalidTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{task_id}/events", response_model=TaskEventListResponse)
async def get_task_events(task_id: str):
    """Get the state transition audit trail for a task."""
    task = await task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    events = await task_manager.get_events(task_id)
    return TaskEventListResponse(events=events)


@router.get("/{task_id}/children", response_model=list[Task])
async def get_child_tasks(task_id: str):
    """Get child tasks (delegations) for a parent task."""
    task = await task_manager.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return await task_manager.get_children(task_id)
