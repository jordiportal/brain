"""Repository for brain_users table."""

import json
from typing import Any, Dict, List, Optional

import structlog

from src.db import get_db

logger = structlog.get_logger()

VALID_ROLES = ("admin", "user", "viewer")


class UserRepository:

    @staticmethod
    async def get_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        db = get_db()
        row = await db.fetch_one(
            "SELECT id, email, password, firstname, lastname, role, is_active, "
            "last_login_at, avatar_url, preferences, created_at, updated_at "
            "FROM brain_users WHERE id = $1",
            user_id,
        )
        return _row_to_dict(row) if row else None

    @staticmethod
    async def get_by_email(email: str) -> Optional[Dict[str, Any]]:
        db = get_db()
        row = await db.fetch_one(
            "SELECT id, email, password, firstname, lastname, role, is_active, "
            "last_login_at, avatar_url, preferences, created_at, updated_at "
            "FROM brain_users WHERE email = $1",
            email,
        )
        return _row_to_dict(row) if row else None

    @staticmethod
    async def get_all(include_inactive: bool = False) -> List[Dict[str, Any]]:
        db = get_db()
        query = (
            "SELECT id, email, firstname, lastname, role, is_active, "
            "last_login_at, avatar_url, preferences, created_at, updated_at "
            "FROM brain_users"
        )
        if not include_inactive:
            query += " WHERE is_active = true"
        query += " ORDER BY id"
        rows = await db.fetch_all(query)
        return [_row_to_dict(r) for r in rows]

    @staticmethod
    async def create(data: Dict[str, Any]) -> Dict[str, Any]:
        db = get_db()
        prefs = data.get("preferences")
        prefs_json = json.dumps(prefs) if prefs else "{}"
        row = await db.fetch_one(
            """
            INSERT INTO brain_users (email, password, firstname, lastname, role, is_active, preferences)
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
            RETURNING id, email, firstname, lastname, role, is_active,
                      last_login_at, avatar_url, preferences, created_at, updated_at
            """,
            data["email"],
            data["password"],
            data.get("firstname"),
            data.get("lastname"),
            data.get("role", "user"),
            data.get("is_active", True),
            prefs_json,
        )
        return _row_to_dict(row)

    @staticmethod
    async def update(user_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        db = get_db()
        sets: list[str] = []
        params: list[Any] = []
        idx = 1

        for field in ("email", "firstname", "lastname", "role", "is_active", "avatar_url"):
            if field in data:
                sets.append(f"{field} = ${idx}")
                params.append(data[field])
                idx += 1

        if "preferences" in data:
            sets.append(f"preferences = ${idx}::jsonb")
            params.append(json.dumps(data["preferences"]))
            idx += 1

        if "password" in data:
            sets.append(f"password = ${idx}")
            params.append(data["password"])
            idx += 1

        if not sets:
            return await UserRepository.get_by_id(user_id)

        sets.append("updated_at = NOW()")
        params.append(user_id)

        query = (
            f"UPDATE brain_users SET {', '.join(sets)} "
            f"WHERE id = ${idx} "
            "RETURNING id, email, firstname, lastname, role, is_active, "
            "last_login_at, avatar_url, preferences, created_at, updated_at"
        )
        row = await db.fetch_one(query, *params)
        return _row_to_dict(row) if row else None

    @staticmethod
    async def delete(user_id: int) -> bool:
        db = get_db()
        result = await db.execute(
            "DELETE FROM brain_users WHERE id = $1", user_id
        )
        return result is not None

    @staticmethod
    async def update_last_login(user_id: int) -> None:
        db = get_db()
        await db.execute(
            "UPDATE brain_users SET last_login_at = NOW() WHERE id = $1",
            user_id,
        )

    @staticmethod
    async def change_password(user_id: int, hashed_password: str) -> bool:
        db = get_db()
        result = await db.execute(
            "UPDATE brain_users SET password = $1, updated_at = NOW() WHERE id = $2",
            hashed_password, user_id,
        )
        return result is not None

    @staticmethod
    async def count_by_role() -> Dict[str, int]:
        db = get_db()
        rows = await db.fetch_all(
            "SELECT role, COUNT(*) as count FROM brain_users GROUP BY role"
        )
        return {r["role"]: r["count"] for r in rows}

    @staticmethod
    async def get_role_permissions(role: str) -> List[Dict[str, Any]]:
        db = get_db()
        rows = await db.fetch_all(
            "SELECT id, role, resource, actions FROM brain_role_permissions WHERE role = $1 ORDER BY resource",
            role,
        )
        return [dict(r) for r in rows]

    @staticmethod
    async def get_all_role_permissions() -> List[Dict[str, Any]]:
        db = get_db()
        rows = await db.fetch_all(
            "SELECT id, role, resource, actions FROM brain_role_permissions ORDER BY role, resource"
        )
        return [dict(r) for r in rows]

    @staticmethod
    async def upsert_role_permission(role: str, resource: str, actions: List[str]) -> Dict[str, Any]:
        db = get_db()
        row = await db.fetch_one(
            """
            INSERT INTO brain_role_permissions (role, resource, actions)
            VALUES ($1, $2, $3)
            ON CONFLICT (role, resource) DO UPDATE SET actions = $3
            RETURNING id, role, resource, actions
            """,
            role, resource, actions,
        )
        return dict(row)

    @staticmethod
    async def delete_role_permission(permission_id: int) -> bool:
        db = get_db()
        result = await db.execute(
            "DELETE FROM brain_role_permissions WHERE id = $1", permission_id
        )
        return result is not None

    @staticmethod
    async def has_permission(role: str, resource: str, action: str) -> bool:
        """Check if a role has a specific permission (checks wildcard too)."""
        db = get_db()
        row = await db.fetch_one(
            """
            SELECT 1 FROM brain_role_permissions
            WHERE role = $1 AND (resource = $2 OR resource = '*') AND $3 = ANY(actions)
            LIMIT 1
            """,
            role, resource, action,
        )
        return row is not None


def _row_to_dict(row) -> Dict[str, Any]:
    d = dict(row)
    if isinstance(d.get("preferences"), str):
        d["preferences"] = json.loads(d["preferences"])
    for ts_field in ("created_at", "updated_at", "last_login_at"):
        val = d.get(ts_field)
        if val and hasattr(val, "isoformat"):
            d[ts_field] = val.isoformat()
    return d
