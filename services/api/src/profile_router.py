"""
Profile & Briefing Router - Endpoints de perfil de usuario y briefing.
Montado en /api/v1/profile
"""

from typing import Any, Optional, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.db.repositories.user_profiles import UserProfileRepository
from src.db.repositories.user_task_results import UserTaskResultRepository

router = APIRouter(prefix="/profile", tags=["Profile"])


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    personal_prompt: Optional[str] = None
    m365_user_id: Optional[str] = None
    timezone: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


@router.get("/{user_id}")
async def get_profile(user_id: str):
    profile = await UserProfileRepository.get(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("/{user_id}")
async def put_profile(user_id: str, body: ProfileUpdate):
    profile = await UserProfileRepository.upsert(user_id, body.model_dump(exclude_none=False))
    return profile


@router.get("/{user_id}/briefing")
async def get_briefing(user_id: str):
    results = await UserTaskResultRepository.get_unread(user_id)
    return {"items": results}


@router.post("/{user_id}/briefing/mark-read")
async def mark_briefing_read(user_id: str):
    count = await UserTaskResultRepository.mark_as_read(user_id)
    return {"marked": count}
