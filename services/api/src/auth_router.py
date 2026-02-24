"""
Auth Router - Authentication endpoints for the GUI.
Uses brain_users table with bcrypt password hashing.
"""

import os
from typing import Optional

import jwt as pyjwt
import structlog
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta

from src.db.repositories.users import UserRepository
from src.auth.dependencies import JWT_SECRET, JWT_ALGORITHM, get_current_user

logger = structlog.get_logger()

router = APIRouter(tags=["Authentication"])

JWT_EXPIRATION_HOURS = int(os.environ.get("JWT_EXPIRATION_HOURS", "168"))  # 7 days


# ===========================================
# Models
# ===========================================

class LoginRequest(BaseModel):
    identifier: str
    password: str


class LoginResponse(BaseModel):
    jwt: str
    user: dict


class UserMeResponse(BaseModel):
    id: int
    email: str
    username: str
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    role: str
    is_active: bool
    blocked: bool
    confirmed: bool
    createdAt: str
    updatedAt: str


class ChangeMyPasswordRequest(BaseModel):
    current_password: str
    new_password: str


# ===========================================
# Helpers
# ===========================================

def _verify_password(plain: str, hashed: str) -> bool:
    try:
        import bcrypt
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def _hash_password(plain: str) -> str:
    import bcrypt
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _create_token(user: dict) -> str:
    payload = {
        "id": user["id"],
        "email": user["email"],
        "role": user.get("role", "user"),
        "firstname": user.get("firstname", ""),
        "lastname": user.get("lastname", ""),
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _user_to_response(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "username": user.get("firstname") or user["email"].split("@")[0],
        "firstname": user.get("firstname"),
        "lastname": user.get("lastname"),
        "role": user.get("role", "user"),
        "is_active": user.get("is_active", True),
        "blocked": not user.get("is_active", True),
        "confirmed": True,
        "createdAt": user.get("created_at", datetime.utcnow().isoformat()),
        "updatedAt": user.get("updated_at", datetime.utcnow().isoformat()),
    }


# ===========================================
# Endpoints
# ===========================================

@router.post("/api/auth/local", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Login - searches brain_users by email. Returns JWT with role."""
    user = await UserRepository.get_by_email(request.identifier)

    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    if not _verify_password(request.password, user["password"]):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    if not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Usuario desactivado")

    await UserRepository.update_last_login(user["id"])

    token = _create_token(user)
    return LoginResponse(jwt=token, user=_user_to_response(user))


@router.get("/api/users/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return the currently authenticated user's data from the DB."""
    user = await UserRepository.get_by_id(current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _user_to_response(user)


@router.put("/api/users/me/password")
async def change_my_password(
    body: ChangeMyPasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    """Allow the current user to change their own password."""
    user = await UserRepository.get_by_id(current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if not _verify_password(body.current_password, user["password"]):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")

    hashed = _hash_password(body.new_password)
    await UserRepository.change_password(user["id"], hashed)
    return {"message": "Contraseña actualizada"}


@router.post("/api/auth/local/register")
async def register():
    """Registration is disabled. Only admins can create users."""
    raise HTTPException(
        status_code=403,
        detail="El registro de usuarios está deshabilitado. Contacte al administrador.",
    )
