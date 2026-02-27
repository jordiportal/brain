"""
FastAPI dependencies for authentication and authorization.

Supports three token types:
  1. Internal JWT (HS256 signed with JWT_SECRET)
  2. Brain API key (sk-brain-*)
  3. Microsoft Entra ID OAuth JWT (RS256, validated via JWKS)

Usage in routers:
    from src.auth import get_current_user, require_role, get_current_user_flexible

    @router.get("/admin-only", dependencies=[Depends(require_role("admin"))])
    async def admin_endpoint():
        ...

    @router.get("/my-data")
    async def my_data(user: dict = Depends(get_current_user)):
        return {"email": user["email"]}

    @router.get("/workspace-file")
    async def ws_file(user: dict = Depends(get_current_user_flexible)):
        return {"user_id": user["email"]}
"""

import os
from typing import Any, Callable, Dict, Optional

import jwt
import structlog
from fastapi import Depends, Header, HTTPException, Query, status

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


async def get_current_user_flexible(
    authorization: Optional[str] = Header(None),
    user_id: Optional[str] = Query(None, alias="user_id"),
    x_brain_user_email: Optional[str] = Header(None, alias="X-Brain-User-Email"),
) -> Dict[str, Any]:
    """
    Flexible auth that tries multiple strategies in order:
      1. Bearer sk-brain-*  -> API key validation
      2. Bearer eyJ*        -> OAuth JWT (Microsoft Entra ID)
      3. Bearer <other>     -> Internal HS256 JWT
      4. ?user_id= query    -> Fallback for internal/service calls (no external auth)

    When authenticated via API key, the X-Brain-User-Email header can override
    the default_user_id to act on behalf of a specific user (trusted proxy pattern).

    Always returns a dict with at least 'email' (used as user_id everywhere).
    """
    if authorization:
        token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization

        # --- API key ---
        if token.startswith("sk-brain-"):
            from src.openai_compat.auth import api_key_validator
            key_data = await api_key_validator.validate_key(token)
            if not key_data:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key inválida")
            uid = key_data.get("permissions", {}).get("default_user_id", "")
            if x_brain_user_email:
                uid = x_brain_user_email
            return {"id": uid, "email": uid, "role": "apikey", "auth_type": "apikey"}

        # --- OAuth JWT (starts with eyJ, typical for JWTs) ---
        if token.startswith("eyJ"):
            from src.openai_compat.oauth import oauth_validator
            if await oauth_validator.is_enabled():
                try:
                    claims = await oauth_validator.validate_token(token)
                    return {
                        "id": claims.oid or claims.user_id,
                        "email": claims.user_id,
                        "role": "user",
                        "firstname": claims.name.split(" ", 1)[0] if claims.name else "",
                        "lastname": claims.name.split(" ", 1)[1] if claims.name and " " in claims.name else "",
                        "auth_type": "oauth",
                    }
                except ValueError:
                    pass  # Fall through to internal JWT

        # --- Internal JWT ---
        payload = _decode_token(token)
        if payload and "id" in payload:
            return {
                "id": payload["id"],
                "email": payload.get("email", ""),
                "role": payload.get("role", "user"),
                "firstname": payload.get("firstname", ""),
                "lastname": payload.get("lastname", ""),
                "auth_type": "jwt",
            }

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    # --- Query param fallback (internal/service calls only) ---
    if user_id:
        return {"id": user_id, "email": user_id, "role": "service", "auth_type": "query"}

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Autenticación requerida")


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
