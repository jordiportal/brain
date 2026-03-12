"""
A2A HTTP+JSON/REST Protocol Binding router (Section 11).

Endpoints:
  POST /message:send          SendMessage
  POST /message:stream        SendStreamingMessage (SSE)
  GET  /tasks/{id}            GetTask
  GET  /tasks                 ListTasks
  POST /tasks/{id}:cancel     CancelTask
  POST /tasks/{id}:subscribe  SubscribeToTask (SSE)
  GET  /extendedAgentCard     GetExtendedAgentCard (authenticated)
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from src.auth.dependencies import get_current_user_flexible, optional_current_user
from src.engine.executor import chain_executor
from src.engine.models import (
    ChainInvokeRequest,
    Message as BrainMessage,
    TaskState as BrainTaskState,
)
from src.engine.registry import chain_registry
from src.engine.task_manager import task_manager, InvalidTransitionError

from .adapter import (
    a2a_message_to_brain,
    brain_task_to_a2a,
    brain_state_to_a2a,
    make_status_update,
)
from .errors import (
    TaskNotFoundError,
    TaskNotCancelableError,
    PushNotificationNotSupportedError,
    UnsupportedOperationError,
)
from .models import (
    A2APart,
    A2AMessage,
    A2ARole,
    A2ATask,
    A2ATaskState,
    A2ATaskStatus,
    SendMessageRequest,
    SendMessageResponse,
    ListTasksResponse,
    StreamResponse,
    TaskStatusUpdateEvent,
    utc_now_iso,
)
from .agent_card import build_agent_card

logger = logging.getLogger(__name__)

router = APIRouter(tags=["A2A Protocol"])


# ── Helpers ──────────────────────────────────────────────────────

def _resolve_chain_id(message: A2AMessage) -> str:
    """Pick chain_id from message metadata or fall back to first registered chain."""
    if message.metadata and "chainId" in message.metadata:
        return message.metadata["chainId"]
    if message.metadata and "agentId" in message.metadata:
        return message.metadata["agentId"]
    ids = chain_registry.list_chain_ids()
    return ids[0] if ids else "brain-default"


def _extract_text(message: A2AMessage) -> str:
    return " ".join(p.text for p in message.parts if p.text) or ""


def _serialize_by_alias(obj) -> str:
    return obj.model_dump_json(by_alias=True, exclude_none=True)


# ── POST /message:send ───────────────────────────────────────────

@router.post("/message:send")
async def send_message(
    body: SendMessageRequest,
    request: Request,
    current_user: Optional[dict] = Depends(optional_current_user),
):
    """A2A SendMessage — synchronous request/response."""
    chain_id = _resolve_chain_id(body.message)
    text = _extract_text(body.message)
    user_id = current_user["email"] if current_user else "a2a-anonymous"
    context_id = body.message.context_id or str(uuid.uuid4())

    if not chain_registry.exists(chain_id):
        chain_id = chain_registry.list_chain_ids()[0] if chain_registry.list_chain_ids() else None
        if not chain_id:
            raise UnsupportedOperationError("No agents available")

    task = await task_manager.create_from_text(
        text,
        chain_id=chain_id,
        context_id=context_id,
        user_id=user_id,
    )
    await task_manager.start(task.id)

    invoke_req = ChainInvokeRequest(input={"message": text})

    try:
        result = await chain_executor.invoke(
            chain_id, invoke_req, context_id, user_id=user_id,
        )
        response_text = (result.output_data or {}).get("response", "")
        if result.status.value == "completed":
            output_msg = BrainMessage.text("agent", response_text)
            task = await task_manager.complete(task.id, output_msg)
        else:
            task = await task_manager.fail(task.id, result.error or "Unknown error")

        await task_manager.update_metrics(
            task.id,
            tokens_used=result.total_tokens,
            duration_ms=result.total_duration_ms,
        )
    except Exception as exc:
        task = await task_manager.fail(task.id, str(exc))

    task = await task_manager.get(task.id) or task
    history_len = body.configuration.history_length if body.configuration else None
    a2a_task = brain_task_to_a2a(task, history_length=history_len)

    resp = SendMessageResponse(task=a2a_task)
    return JSONResponse(
        content=json.loads(_serialize_by_alias(resp)),
        media_type="application/json",
    )


# ── POST /message:stream ─────────────────────────────────────────

@router.post("/message:stream")
async def send_streaming_message(
    body: SendMessageRequest,
    request: Request,
    current_user: Optional[dict] = Depends(optional_current_user),
):
    """A2A SendStreamingMessage — SSE stream of StreamResponse frames."""
    chain_id = _resolve_chain_id(body.message)
    text = _extract_text(body.message)
    user_id = current_user["email"] if current_user else "a2a-anonymous"
    context_id = body.message.context_id or str(uuid.uuid4())

    if not chain_registry.exists(chain_id):
        chain_id = chain_registry.list_chain_ids()[0] if chain_registry.list_chain_ids() else None
        if not chain_id:
            raise UnsupportedOperationError("No agents available")

    task = await task_manager.create_from_text(
        text, chain_id=chain_id, context_id=context_id, user_id=user_id,
    )

    async def _stream():
        await task_manager.start(task.id)

        # Initial task snapshot
        cur = await task_manager.get(task.id) or task
        frame = StreamResponse(task=brain_task_to_a2a(cur))
        yield f"data: {_serialize_by_alias(frame)}\n\n"

        invoke_req = ChainInvokeRequest(input={"message": text})
        full_response = ""

        try:
            async for event in chain_executor.invoke_stream(
                chain_id, invoke_req, context_id, user_id=user_id,
            ):
                if event.event_type == "token" and event.content:
                    full_response += event.content
                    status_evt = TaskStatusUpdateEvent(
                        task_id=task.id,
                        context_id=context_id,
                        status=A2ATaskStatus(
                            state=A2ATaskState.TASK_STATE_WORKING,
                            message=A2AMessage(
                                role=A2ARole.ROLE_AGENT,
                                parts=[A2APart(text=event.content)],
                            ),
                            timestamp=utc_now_iso(),
                        ),
                    )
                    frame = StreamResponse(task_status_update=status_evt)
                    yield f"data: {_serialize_by_alias(frame)}\n\n"

                elif event.event_type == "error":
                    err_msg = event.data.get("error", "Unknown error")
                    await task_manager.fail(task.id, err_msg)
                    cur = await task_manager.get(task.id) or task
                    frame = StreamResponse(task=brain_task_to_a2a(cur))
                    yield f"data: {_serialize_by_alias(frame)}\n\n"
                    return

            output_msg = BrainMessage.text("agent", full_response)
            await task_manager.complete(task.id, output_msg)
        except Exception as exc:
            await task_manager.fail(task.id, str(exc))

        cur = await task_manager.get(task.id) or task
        frame = StreamResponse(task=brain_task_to_a2a(cur))
        yield f"data: {_serialize_by_alias(frame)}\n\n"

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── GET /tasks/{id} ──────────────────────────────────────────────

@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    history_length: Optional[int] = Query(None, alias="historyLength"),
    current_user: Optional[dict] = Depends(optional_current_user),
):
    """A2A GetTask."""
    task = await task_manager.get(task_id)
    if not task:
        raise TaskNotFoundError(task_id)

    a2a_task = brain_task_to_a2a(task, history_length=history_length)
    return JSONResponse(
        content=json.loads(_serialize_by_alias(a2a_task)),
        media_type="application/json",
    )


# ── GET /tasks ────────────────────────────────────────────────────

@router.get("/tasks")
async def list_tasks(
    context_id: Optional[str] = Query(None, alias="contextId"),
    page_size: int = Query(50, alias="pageSize", ge=1, le=200),
    page_token: Optional[str] = Query(None, alias="pageToken"),
    current_user: Optional[dict] = Depends(optional_current_user),
):
    """A2A ListTasks."""
    from src.engine.models import TaskFilters

    offset = int(page_token) if page_token else 0
    filters = TaskFilters(
        context_id=context_id,
        limit=page_size,
        offset=offset,
    )
    tasks = await task_manager.list(filters)
    total = await task_manager.count(filters)

    a2a_tasks = [brain_task_to_a2a(t) for t in tasks]
    next_offset = offset + page_size
    next_token = str(next_offset) if next_offset < total else None

    resp = ListTasksResponse(tasks=a2a_tasks, next_page_token=next_token)
    return JSONResponse(
        content=json.loads(_serialize_by_alias(resp)),
        media_type="application/json",
    )


# ── POST /tasks/{id}:cancel ──────────────────────────────────────

@router.post("/tasks/{task_id}:cancel")
async def cancel_task(
    task_id: str,
    current_user: Optional[dict] = Depends(optional_current_user),
):
    """A2A CancelTask."""
    task = await task_manager.get(task_id)
    if not task:
        raise TaskNotFoundError(task_id)

    try:
        task = await task_manager.cancel(task_id)
    except InvalidTransitionError:
        raise TaskNotCancelableError(task_id, brain_state_to_a2a(task.state).value)

    a2a_task = brain_task_to_a2a(task)
    return JSONResponse(
        content=json.loads(_serialize_by_alias(a2a_task)),
        media_type="application/json",
    )


# ── POST /tasks/{id}:subscribe ───────────────────────────────────

@router.post("/tasks/{task_id}:subscribe")
async def subscribe_to_task(
    task_id: str,
    current_user: Optional[dict] = Depends(optional_current_user),
):
    """A2A SubscribeToTask — poll-based SSE stream until terminal state."""
    task = await task_manager.get(task_id)
    if not task:
        raise TaskNotFoundError(task_id)

    if task.is_terminal:
        raise UnsupportedOperationError(
            f"Task {task_id} is in terminal state {task.state.value}"
        )

    async def _poll():
        last_state = task.state
        frame = StreamResponse(task=brain_task_to_a2a(task))
        yield f"data: {_serialize_by_alias(frame)}\n\n"

        while True:
            await asyncio.sleep(1)
            current = await task_manager.get(task_id)
            if not current:
                break
            if current.state != last_state or current.updated_at != task.updated_at:
                last_state = current.state
                frame = StreamResponse(task=brain_task_to_a2a(current))
                yield f"data: {_serialize_by_alias(frame)}\n\n"
                if current.is_terminal:
                    break

    return StreamingResponse(
        _poll(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Push notification stubs (not supported) ──────────────────────

@router.post("/tasks/{task_id}/pushNotificationConfigs")
async def create_push_config(task_id: str):
    raise PushNotificationNotSupportedError()


@router.get("/tasks/{task_id}/pushNotificationConfigs")
async def list_push_configs(task_id: str):
    raise PushNotificationNotSupportedError()


@router.get("/tasks/{task_id}/pushNotificationConfigs/{config_id}")
async def get_push_config(task_id: str, config_id: str):
    raise PushNotificationNotSupportedError()


@router.delete("/tasks/{task_id}/pushNotificationConfigs/{config_id}")
async def delete_push_config(task_id: str, config_id: str):
    raise PushNotificationNotSupportedError()


# ── GET /extendedAgentCard ────────────────────────────────────────

@router.get("/extendedAgentCard")
async def get_extended_agent_card(
    request: Request,
    current_user: dict = Depends(get_current_user_flexible),
):
    """A2A GetExtendedAgentCard (authenticated)."""
    base_url = str(request.base_url).rstrip("/")
    card = await build_agent_card(base_url=base_url)
    return JSONResponse(
        content=json.loads(_serialize_by_alias(card)),
        media_type="application/json",
    )
