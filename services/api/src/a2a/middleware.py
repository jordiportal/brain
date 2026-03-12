"""
A2A middleware — validates and propagates A2A service parameters.

Section 3.2.6 / 11.2: A2A-Version and A2A-Extensions headers.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .errors import VersionNotSupportedError

SUPPORTED_VERSIONS = {"1.0", "0.3"}
A2A_PATH_PREFIX = "/a2a"


class A2AVersionMiddleware(BaseHTTPMiddleware):
    """
    For requests under the A2A path prefix:
    - Validates A2A-Version header if present
    - Propagates A2A-Version on response
    - Passes A2A-Extensions through
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if not path.startswith(A2A_PATH_PREFIX) and path != "/.well-known/agent-card.json":
            return await call_next(request)

        requested_version = request.headers.get("A2A-Version", "").strip()
        if requested_version and requested_version not in SUPPORTED_VERSIONS:
            err = VersionNotSupportedError(requested_version)
            return err.to_response()

        response = await call_next(request)

        response.headers["A2A-Version"] = "1.0"

        extensions = request.headers.get("A2A-Extensions", "")
        if extensions:
            response.headers["A2A-Extensions"] = extensions

        return response
