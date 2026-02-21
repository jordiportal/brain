"""Repository for user_profiles table."""

import json
from typing import Any, Dict, List, Optional

from src.db import get_db


class UserProfileRepository:

    @staticmethod
    async def get(user_id: str) -> Optional[Dict[str, Any]]:
        db = get_db()
        row = await db.fetch_one(
            "SELECT user_id, display_name, personal_prompt, m365_user_id, "
            "timezone, preferences, created_at, updated_at "
            "FROM user_profiles WHERE user_id = $1",
            user_id,
        )
        if row is None:
            return None
        d = dict(row)
        if isinstance(d.get("preferences"), str):
            d["preferences"] = json.loads(d["preferences"])
        return d

    @staticmethod
    async def upsert(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        db = get_db()
        prefs = data.get("preferences")
        prefs_json = json.dumps(prefs) if prefs is not None else None
        row = await db.fetch_one(
            """
            INSERT INTO user_profiles (user_id, display_name, personal_prompt, m365_user_id, timezone, preferences)
            VALUES ($1, $2, $3, $4, $5, COALESCE($6::jsonb, '{}'::jsonb))
            ON CONFLICT (user_id) DO UPDATE SET
                display_name   = COALESCE(EXCLUDED.display_name, user_profiles.display_name),
                personal_prompt = COALESCE(EXCLUDED.personal_prompt, user_profiles.personal_prompt),
                m365_user_id   = COALESCE(EXCLUDED.m365_user_id, user_profiles.m365_user_id),
                timezone       = COALESCE(EXCLUDED.timezone, user_profiles.timezone),
                preferences    = COALESCE(EXCLUDED.preferences, user_profiles.preferences),
                updated_at     = NOW()
            RETURNING user_id, display_name, personal_prompt, m365_user_id, timezone, preferences, created_at, updated_at
            """,
            user_id,
            data.get("display_name"),
            data.get("personal_prompt"),
            data.get("m365_user_id"),
            data.get("timezone"),
            prefs_json,
        )
        d = dict(row)
        if isinstance(d.get("preferences"), str):
            d["preferences"] = json.loads(d["preferences"])
        return d
