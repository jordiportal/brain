"""
FastAPI dependencies for authentication and authorization.

Usage in routers:
    from src.auth import get_current_user, require_role

    @router.get("/admin-only", dependencies=[Depends(require_role("admin"))])
    async def admin_endpoint():
        ...

    @router.get("/my-data")
    async def my_data(user: dict = Depends(get_current_user)):
        return {"email": user["email"]}
"""

import os
from typing import Any, Callable, Dict, Optional

import jwt
import structlog
from fastapi import Depends, Header, HTTPException, status

from src.db.repositories.users import UserRepository

logger = structlog.get_logger()

JWT_SECRET = os.environ.get("JWT_SECRET", "brain-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"


def _decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expirado")
    except jwt.InvalidTokenError:
        return None


async def get_current_user(authorization: str = Header(None)) -> Dict[str, Any]:
    """
    Extract and validate the current user from the Authorization header.
    Returns a dict with id, email, role, firstname, lastname.
    """
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token requerido")

    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization

    payload = _decode_token(token)
    if not payload or "id" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    return {
        "id": payload["id"],
        "email": payload.get("email", ""),
        "role": payload.get("role", "user"),
        "firstname": payload.get("firstname", ""),
        "lastname": payload.get("lastname", ""),
    }


async def optional_current_user(authorization: str = Header(None)) -> Optional[Dict[str, Any]]:
    """Like get_current_user but returns None instead of raising on missing/invalid token."""
    if not authorization:
        return None
    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None


def require_role(*allowed_roles: str) -> Callable:
    """
    Factory that returns a FastAPI dependency checking the user's role.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_role("admin"))])
    """
    async def _check(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if user["role"] not in allowed_roles:
            logger.warning("Access denied", user_email=user["email"], user_role=user["role"], required=allowed_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere rol: {', '.join(allowed_roles)}"
            )
        return user
    return _check


def require_permission(resource: str, action: str) -> Callable:
    """
    Factory that returns a dependency checking granular permission from brain_role_permissions.

    Usage:
        @router.post("/rag/upload", dependencies=[Depends(require_permission("rag", "write"))])
    """
    async def _check(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        has = await UserRepository.has_permission(user["role"], resource, action)
        if not has:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Sin permiso: {resource}/{action}"
            )
        return user
    return _check
