"""
A2A Adapter — bidirectional translation between Brain internal models and A2A protocol models.
"""

from __future__ import annotations

from datetime import timezone
from typing import Optional

from src.engine.models import (
    Task as BrainTask,
    TaskState as BrainTaskState,
    Message as BrainMessage,
    Part as BrainPart,
    Artifact as BrainArtifact,
)
from .models import (
    A2APart,
    A2AMessage,
    A2ATask,
    A2ATaskState,
    A2ATaskStatus,
    A2AArtifact,
    A2ARole,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
    utc_now_iso,
)


# ── State mapping ────────────────────────────────────────────────

_BRAIN_TO_A2A_STATE: dict[str, A2ATaskState] = {
    "submitted": A2ATaskState.TASK_STATE_SUBMITTED,
    "working": A2ATaskState.TASK_STATE_WORKING,
    "input_required": A2ATaskState.TASK_STATE_INPUT_REQUIRED,
    "auth_required": A2ATaskState.TASK_STATE_AUTH_REQUIRED,
    "completed": A2ATaskState.TASK_STATE_COMPLETED,
    "failed": A2ATaskState.TASK_STATE_FAILED,
    "canceled": A2ATaskState.TASK_STATE_CANCELED,
    "rejected": A2ATaskState.TASK_STATE_REJECTED,
}

_A2A_TO_BRAIN_STATE: dict[A2ATaskState, str] = {
    v: k for k, v in _BRAIN_TO_A2A_STATE.items()
}


def brain_state_to_a2a(state: BrainTaskState) -> A2ATaskState:
    return _BRAIN_TO_A2A_STATE.get(state.value, A2ATaskState.TASK_STATE_UNSPECIFIED)


def a2a_state_to_brain(state: A2ATaskState) -> Optional[BrainTaskState]:
    val = _A2A_TO_BRAIN_STATE.get(state)
    if val is None:
        return None
    return BrainTaskState(val)


# ── Role mapping ─────────────────────────────────────────────────

_BRAIN_ROLE_TO_A2A: dict[str, A2ARole] = {
    "user": A2ARole.ROLE_USER,
    "agent": A2ARole.ROLE_AGENT,
    "system": A2ARole.ROLE_AGENT,
    "tool": A2ARole.ROLE_AGENT,
}


def brain_role_to_a2a(role: str) -> A2ARole:
    return _BRAIN_ROLE_TO_A2A.get(role, A2ARole.ROLE_AGENT)


def a2a_role_to_brain(role: A2ARole) -> str:
    if role == A2ARole.ROLE_USER:
        return "user"
    return "agent"


# ── Part conversion ──────────────────────────────────────────────

def brain_part_to_a2a(part: BrainPart) -> A2APart:
    a2a = A2APart(
        media_type=part.media_type,
        filename=part.filename,
    )
    if part.type == "text" and part.text is not None:
        a2a.text = part.text
    elif part.type == "data" and part.data is not None:
        a2a.data = part.data
    elif part.type in ("file", "image", "video") and part.url is not None:
        a2a.url = part.url
        if not a2a.media_type:
            _type_to_mime = {"image": "image/*", "video": "video/*", "file": "application/octet-stream"}
            a2a.media_type = _type_to_mime.get(part.type)
    elif part.text is not None:
        a2a.text = part.text
    return a2a


def a2a_part_to_brain(part: A2APart) -> BrainPart:
    if part.text is not None:
        return BrainPart(type="text", text=part.text, media_type=part.media_type, filename=part.filename)
    if part.data is not None:
        return BrainPart(type="data", data=part.data if isinstance(part.data, dict) else {"value": part.data},
                         media_type=part.media_type, filename=part.filename)
    if part.url is not None:
        ptype = "file"
        if part.media_type:
            if part.media_type.startswith("image/"):
                ptype = "image"
            elif part.media_type.startswith("video/"):
                ptype = "video"
        return BrainPart(type=ptype, url=part.url, media_type=part.media_type, filename=part.filename)
    if part.raw is not None:
        return BrainPart(type="file", data={"raw_base64": part.raw}, media_type=part.media_type, filename=part.filename)
    return BrainPart(type="text", text="")


# ── Message conversion ───────────────────────────────────────────

def brain_message_to_a2a(
    msg: BrainMessage,
    *,
    context_id: Optional[str] = None,
    task_id: Optional[str] = None,
) -> A2AMessage:
    return A2AMessage(
        message_id=msg.id,
        context_id=context_id,
        task_id=task_id,
        role=brain_role_to_a2a(msg.role),
        parts=[brain_part_to_a2a(p) for p in msg.parts],
        metadata=msg.metadata if msg.metadata else None,
    )


def a2a_message_to_brain(msg: A2AMessage) -> BrainMessage:
    return BrainMessage(
        id=msg.message_id,
        role=a2a_role_to_brain(msg.role),
        parts=[a2a_part_to_brain(p) for p in msg.parts],
        metadata=msg.metadata or {},
    )


# ── Artifact conversion ─────────────────────────────────────────

def brain_artifact_to_a2a(art: BrainArtifact) -> A2AArtifact:
    return A2AArtifact(
        artifact_id=art.id,
        name=art.name,
        description=art.description,
        parts=[brain_part_to_a2a(p) for p in art.parts],
        metadata=art.metadata if art.metadata else None,
    )


def a2a_artifact_to_brain(art: A2AArtifact) -> BrainArtifact:
    return BrainArtifact(
        id=art.artifact_id,
        name=art.name or "artifact",
        description=art.description,
        parts=[a2a_part_to_brain(p) for p in art.parts],
        metadata=art.metadata or {},
    )


# ── Task conversion ─────────────────────────────────────────────

def _dt_to_iso(dt) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def brain_task_to_a2a(
    task: BrainTask,
    *,
    history_length: Optional[int] = None,
) -> A2ATask:
    status_message = None
    if task.output:
        status_message = brain_message_to_a2a(
            task.output, context_id=task.context_id, task_id=task.id
        )
    elif task.state_reason:
        status_message = A2AMessage(
            role=A2ARole.ROLE_AGENT,
            parts=[A2APart(text=task.state_reason)],
        )

    status = A2ATaskStatus(
        state=brain_state_to_a2a(task.state),
        message=status_message,
        timestamp=_dt_to_iso(task.updated_at) or utc_now_iso(),
    )

    history = [
        brain_message_to_a2a(m, context_id=task.context_id, task_id=task.id)
        for m in task.history
    ]
    if history_length is not None and history_length >= 0:
        history = history[-history_length:] if history_length > 0 else []

    artifacts = [brain_artifact_to_a2a(a) for a in task.artifacts]

    return A2ATask(
        id=task.id,
        context_id=task.context_id,
        status=status,
        artifacts=artifacts,
        history=history,
        metadata=task.metadata if task.metadata else None,
    )


# ── Event helpers ────────────────────────────────────────────────

def make_status_update(task: BrainTask, reason: Optional[str] = None) -> TaskStatusUpdateEvent:
    msg = None
    if reason:
        msg = A2AMessage(role=A2ARole.ROLE_AGENT, parts=[A2APart(text=reason)])
    return TaskStatusUpdateEvent(
        task_id=task.id,
        context_id=task.context_id,
        status=A2ATaskStatus(
            state=brain_state_to_a2a(task.state),
            message=msg,
            timestamp=utc_now_iso(),
        ),
    )


def make_artifact_update(
    task: BrainTask,
    artifact: BrainArtifact,
    *,
    append: bool = False,
    last_chunk: bool = True,
) -> TaskArtifactUpdateEvent:
    return TaskArtifactUpdateEvent(
        task_id=task.id,
        context_id=task.context_id,
        artifact=brain_artifact_to_a2a(artifact),
        append=append,
        last_chunk=last_chunk,
    )
