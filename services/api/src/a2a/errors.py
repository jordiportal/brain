"""
A2A error handling — RFC 9457 Problem Details for HTTP+JSON/REST binding.

Maps A2A-specific error types to HTTP status codes and type URIs
as defined in specification Section 5.4.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


_A2A_ERROR_BASE = "https://a2a-protocol.org/errors"


class A2AProblemDetail(Exception):
    """Base for all A2A errors surfaced as RFC 9457 Problem Details."""

    def __init__(
        self,
        *,
        type_suffix: str,
        title: str,
        status: int,
        detail: str,
        extra: dict | None = None,
    ):
        self.type_uri = f"{_A2A_ERROR_BASE}/{type_suffix}"
        self.title = title
        self.status = status
        self.detail = detail
        self.extra = extra or {}
        super().__init__(detail)

    def to_response(self) -> JSONResponse:
        body: dict = {
            "type": self.type_uri,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            **self.extra,
        }
        return JSONResponse(
            status_code=self.status,
            content=body,
            media_type="application/problem+json",
        )


# ── Concrete error types (Section 5.4) ──────────────────────────

class TaskNotFoundError(A2AProblemDetail):
    def __init__(self, task_id: str):
        super().__init__(
            type_suffix="task-not-found",
            title="Task Not Found",
            status=404,
            detail="The specified task ID does not exist or is not accessible",
            extra={"taskId": task_id},
        )


class TaskNotCancelableError(A2AProblemDetail):
    def __init__(self, task_id: str, current_state: str):
        super().__init__(
            type_suffix="task-not-cancelable",
            title="Task Not Cancelable",
            status=409,
            detail=f"Task is in {current_state} state and cannot be canceled",
            extra={"taskId": task_id, "currentState": current_state},
        )


class PushNotificationNotSupportedError(A2AProblemDetail):
    def __init__(self):
        super().__init__(
            type_suffix="push-notification-not-supported",
            title="Push Notification Not Supported",
            status=400,
            detail="This agent does not support push notifications",
        )


class UnsupportedOperationError(A2AProblemDetail):
    def __init__(self, operation: str):
        super().__init__(
            type_suffix="unsupported-operation",
            title="Unsupported Operation",
            status=400,
            detail=f"The operation '{operation}' is not supported by this agent",
        )


class ContentTypeNotSupportedError(A2AProblemDetail):
    def __init__(self, content_type: str):
        super().__init__(
            type_suffix="content-type-not-supported",
            title="Content Type Not Supported",
            status=415,
            detail=f"Content type '{content_type}' is not supported",
        )


class InvalidAgentResponseError(A2AProblemDetail):
    def __init__(self, detail: str = "The agent produced an invalid response"):
        super().__init__(
            type_suffix="invalid-agent-response",
            title="Invalid Agent Response",
            status=502,
            detail=detail,
        )


class VersionNotSupportedError(A2AProblemDetail):
    def __init__(self, version: str):
        super().__init__(
            type_suffix="version-not-supported",
            title="Version Not Supported",
            status=400,
            detail=f"A2A protocol version '{version}' is not supported. Supported: 1.0",
            extra={"requestedVersion": version, "supportedVersions": ["1.0"]},
        )


# ── FastAPI exception handler ────────────────────────────────────

async def a2a_problem_handler(_request: Request, exc: A2AProblemDetail) -> JSONResponse:
    return exc.to_response()
