"""
User Management Router - CRUD for brain_users + role permissions.
All endpoints require admin role except where noted.
"""

from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from src.auth import get_current_user, require_role
from src.db.repositories.users import UserRepository, VALID_ROLES

logger = structlog.get_logger()

router = APIRouter(prefix="/users", tags=["User Management"])


# ===========================================
# Models
# ===========================================

class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    role: str = "user"
    is_active: bool = True


class UpdateUserRequest(BaseModel):
    email: Optional[EmailStr] = None
    firstname: Optional[str] = None
    lastname: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class AdminChangePasswordRequest(BaseModel):
    new_password: str


class RolePermissionRequest(BaseModel):
    resource: str
    actions: List[str]


# ===========================================
# User CRUD (admin only)
# ===========================================

@router.get("", dependencies=[Depends(require_role("admin"))])
async def list_users(include_inactive: bool = False):
    """List all users."""
    users = await UserRepository.get_all(include_inactive=include_inactive)
    for u in users:
        u.pop("password", None)
    stats = await UserRepository.count_by_role()
    return {"users": users, "stats": stats, "total": len(users)}


@router.post("", dependencies=[Depends(require_role("admin"))])
async def create_user(body: CreateUserRequest):
    """Create a new user (admin only)."""
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Rol inválido. Válidos: {', '.join(VALID_ROLES)}")

    existing = await UserRepository.get_by_email(body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese email")

    import bcrypt
    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()

    user = await UserRepository.create({
        "email": body.email,
        "password": hashed,
        "firstname": body.firstname,
        "lastname": body.lastname,
        "role": body.role,
        "is_active": body.is_active,
    })
    user.pop("password", None)
    return user


@router.get("/{user_id}", dependencies=[Depends(require_role("admin"))])
async def get_user(user_id: int):
    """Get a single user by ID."""
    user = await UserRepository.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user.pop("password", None)
    return user


@router.put("/{user_id}", dependencies=[Depends(require_role("admin"))])
async def update_user(user_id: int, body: UpdateUserRequest):
    """Update a user (admin only)."""
    if body.role and body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Rol inválido. Válidos: {', '.join(VALID_ROLES)}")

    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")

    user = await UserRepository.update(user_id, data)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user.pop("password", None)
    return user


@router.delete("/{user_id}")
async def delete_user(user_id: int, admin: dict = Depends(require_role("admin"))):
    """Delete a user (admin only). Cannot delete yourself."""
    if admin["id"] == user_id:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")

    target = await UserRepository.get_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    await UserRepository.delete(user_id)
    return {"message": "Usuario eliminado", "id": user_id}


@router.put("/{user_id}/password", dependencies=[Depends(require_role("admin"))])
async def admin_change_password(user_id: int, body: AdminChangePasswordRequest):
    """Admin: set a user's password directly."""
    user = await UserRepository.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    import bcrypt
    hashed = bcrypt.hashpw(body.new_password.encode(), bcrypt.gensalt()).decode()
    await UserRepository.change_password(user_id, hashed)
    return {"message": "Contraseña actualizada"}


# ===========================================
# Roles & Permissions
# ===========================================

@router.get("/roles/list", dependencies=[Depends(require_role("admin"))])
async def list_roles():
    """List available roles and their stats."""
    stats = await UserRepository.count_by_role()
    roles = []
    for r in VALID_ROLES:
        perms = await UserRepository.get_role_permissions(r)
        roles.append({
            "name": r,
            "user_count": stats.get(r, 0),
            "permissions": perms,
        })
    return {"roles": roles}


@router.get("/roles/{role}/permissions", dependencies=[Depends(require_role("admin"))])
async def get_role_permissions(role: str):
    """Get permissions for a specific role."""
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Rol inválido. Válidos: {', '.join(VALID_ROLES)}")
    perms = await UserRepository.get_role_permissions(role)
    return {"role": role, "permissions": perms}


@router.put("/roles/{role}/permissions", dependencies=[Depends(require_role("admin"))])
async def update_role_permissions(role: str, body: RolePermissionRequest):
    """Create or update a permission entry for a role."""
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Rol inválido. Válidos: {', '.join(VALID_ROLES)}")
    perm = await UserRepository.upsert_role_permission(role, body.resource, body.actions)
    return perm


@router.delete("/roles/{role}/permissions/{permission_id}", dependencies=[Depends(require_role("admin"))])
async def delete_role_permission(role: str, permission_id: int):
    """Delete a specific permission entry."""
    await UserRepository.delete_role_permission(permission_id)
    return {"message": "Permiso eliminado"}
