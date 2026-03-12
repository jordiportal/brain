"""
A2A Protocol data models (RC v1.0).

Pydantic models that mirror the canonical A2A proto definitions with:
- camelCase JSON serialization (Section 5.5)
- SCREAMING_SNAKE_CASE enum values (ProtoJSON)
- ISO 8601 UTC timestamps (Section 5.6.1)
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Union
from pydantic import BaseModel, ConfigDict, Field
import uuid


def _to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(w.capitalize() for w in parts[1:])


class _CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        ser_json_timedelta="iso8601",
    )


# ── Enums (ProtoJSON: SCREAMING_SNAKE_CASE) ─────────────────────

class A2ATaskState(str, Enum):
    TASK_STATE_UNSPECIFIED = "TASK_STATE_UNSPECIFIED"
    TASK_STATE_SUBMITTED = "TASK_STATE_SUBMITTED"
    TASK_STATE_WORKING = "TASK_STATE_WORKING"
    TASK_STATE_COMPLETED = "TASK_STATE_COMPLETED"
    TASK_STATE_FAILED = "TASK_STATE_FAILED"
    TASK_STATE_CANCELED = "TASK_STATE_CANCELED"
    TASK_STATE_INPUT_REQUIRED = "TASK_STATE_INPUT_REQUIRED"
    TASK_STATE_REJECTED = "TASK_STATE_REJECTED"
    TASK_STATE_AUTH_REQUIRED = "TASK_STATE_AUTH_REQUIRED"


class A2ARole(str, Enum):
    ROLE_UNSPECIFIED = "ROLE_UNSPECIFIED"
    ROLE_USER = "ROLE_USER"
    ROLE_AGENT = "ROLE_AGENT"


# ── Core data objects ────────────────────────────────────────────

class A2APart(_CamelModel):
    """Section 4.1.5 — smallest content unit."""
    text: Optional[str] = None
    raw: Optional[str] = None  # base64 in JSON
    url: Optional[str] = None
    data: Optional[Any] = None
    metadata: Optional[dict[str, Any]] = None
    filename: Optional[str] = None
    media_type: Optional[str] = None


class A2AMessage(_CamelModel):
    """Section 4.1.4 — one communication turn."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    context_id: Optional[str] = None
    task_id: Optional[str] = None
    role: A2ARole
    parts: list[A2APart]
    metadata: Optional[dict[str, Any]] = None
    extensions: list[str] = Field(default_factory=list)
    reference_task_ids: list[str] = Field(default_factory=list)


class A2ATaskStatus(_CamelModel):
    """Section 4.1.2 — current task status."""
    state: A2ATaskState
    message: Optional[A2AMessage] = None
    timestamp: Optional[str] = None  # ISO 8601


class A2AArtifact(_CamelModel):
    """Section 4.1.6 — task output."""
    artifact_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: Optional[str] = None
    description: Optional[str] = None
    parts: list[A2APart]
    metadata: Optional[dict[str, Any]] = None
    extensions: list[str] = Field(default_factory=list)


class A2ATask(_CamelModel):
    """Section 4.1.1 — fundamental work unit."""
    id: str
    context_id: Optional[str] = None
    status: A2ATaskStatus
    artifacts: list[A2AArtifact] = Field(default_factory=list)
    history: list[A2AMessage] = Field(default_factory=list)
    metadata: Optional[dict[str, Any]] = None


# ── Streaming events ─────────────────────────────────────────────

class TaskStatusUpdateEvent(_CamelModel):
    task_id: str
    context_id: str
    status: A2ATaskStatus
    metadata: Optional[dict[str, Any]] = None


class TaskArtifactUpdateEvent(_CamelModel):
    task_id: str
    context_id: str
    artifact: A2AArtifact
    append: bool = False
    last_chunk: bool = False
    metadata: Optional[dict[str, Any]] = None


class StreamResponse(_CamelModel):
    """Discriminated union for SSE data frames."""
    task: Optional[A2ATask] = None
    message: Optional[A2AMessage] = None
    task_status_update: Optional[TaskStatusUpdateEvent] = None
    task_artifact_update: Optional[TaskArtifactUpdateEvent] = None


# ── Request / Response ───────────────────────────────────────────

class SendMessageConfiguration(_CamelModel):
    accepted_output_modes: list[str] = Field(default_factory=list)
    history_length: Optional[int] = None
    blocking: bool = False


class SendMessageRequest(_CamelModel):
    message: A2AMessage
    configuration: Optional[SendMessageConfiguration] = None


class SendMessageResponse(_CamelModel):
    """SendMessage returns either a Task or a standalone Message."""
    task: Optional[A2ATask] = None
    message: Optional[A2AMessage] = None


class ListTasksRequest(_CamelModel):
    context_id: Optional[str] = None
    page_size: int = 50
    page_token: Optional[str] = None


class ListTasksResponse(_CamelModel):
    tasks: list[A2ATask] = Field(default_factory=list)
    next_page_token: Optional[str] = None


# ── Agent Card ───────────────────────────────────────────────────

class AgentProvider(_CamelModel):
    url: str
    organization: str


class AgentInterface(_CamelModel):
    url: str
    protocol_binding: str  # "JSONRPC" | "GRPC" | "HTTP+JSON"
    protocol_version: str
    tenant: Optional[str] = None


class AgentCapabilities(_CamelModel):
    streaming: Optional[bool] = None
    push_notifications: Optional[bool] = None
    extended_agent_card: Optional[bool] = None


class AgentSkill(_CamelModel):
    id: str
    name: str
    description: str
    tags: list[str]
    examples: list[str] = Field(default_factory=list)
    input_modes: list[str] = Field(default_factory=list)
    output_modes: list[str] = Field(default_factory=list)


class APIKeySecurityScheme(_CamelModel):
    description: Optional[str] = None
    location: str  # "query" | "header" | "cookie"
    name: str


class HTTPAuthSecurityScheme(_CamelModel):
    description: Optional[str] = None
    scheme: str  # "Bearer", "Basic"
    bearer_format: Optional[str] = None


class SecurityScheme(_CamelModel):
    api_key_security_scheme: Optional[APIKeySecurityScheme] = None
    http_auth_security_scheme: Optional[HTTPAuthSecurityScheme] = None


class SecurityRequirement(_CamelModel):
    schemes: dict[str, list[str]] = Field(default_factory=dict)


class AgentCard(_CamelModel):
    name: str
    description: str
    supported_interfaces: list[AgentInterface]
    provider: Optional[AgentProvider] = None
    version: str
    documentation_url: Optional[str] = None
    capabilities: AgentCapabilities
    security_schemes: dict[str, SecurityScheme] = Field(default_factory=dict)
    security_requirements: list[SecurityRequirement] = Field(default_factory=list)
    default_input_modes: list[str]
    default_output_modes: list[str]
    skills: list[AgentSkill]
    icon_url: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
           f"{datetime.now(timezone.utc).microsecond // 1000:03d}Z"
