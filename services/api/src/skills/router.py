"""
REST endpoints for the Skills Sync service.

Provides manual sync trigger, status check, and repo info.
"""

from fastapi import APIRouter, HTTPException
import structlog

from .sync_service import skill_sync_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/skills", tags=["Skills Sync"])


@router.post("/sync")
async def trigger_sync():
    """Trigger a manual synchronisation from the skills Git repository."""
    if not skill_sync_service.is_configured:
        raise HTTPException(
            status_code=400,
            detail="Skills repository not configured. Set SKILLS_REPO_URL.",
        )

    if skill_sync_service.status.in_progress:
        raise HTTPException(status_code=409, detail="Sync already in progress.")

    status = await skill_sync_service.sync()
    return {
        "status": "ok" if not status.errors else "partial",
        "skills_synced": status.skills_synced,
        "agents_updated": status.agents_updated,
        "commit": status.last_commit,
        "branch": status.branch,
        "duration_ms": status.duration_ms,
        "errors": status.errors,
    }


@router.get("/sync/status")
async def get_sync_status():
    """Return the current sync status."""
    s = skill_sync_service.status
    return {
        "configured": skill_sync_service.is_configured,
        "in_progress": s.in_progress,
        "last_sync": s.last_sync.isoformat() if s.last_sync else None,
        "last_commit": s.last_commit,
        "branch": s.branch,
        "repo_url": s.repo_url,
        "skills_synced": s.skills_synced,
        "agents_updated": s.agents_updated,
        "duration_ms": s.duration_ms,
        "errors": s.errors,
    }


@router.get("/repo-info")
async def get_repo_info():
    """Return the skills repository configuration (no secrets)."""
    return skill_sync_service.get_repo_info()
