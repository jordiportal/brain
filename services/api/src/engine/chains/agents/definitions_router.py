"""
Router CRUD para Agent Definitions (tabla agent_definitions).

Permite crear, leer, actualizar, eliminar agentes y gestionar versiones.
Cada update guarda un snapshot automatico para rollback.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import structlog

from src.db.repositories.agent_definitions import AgentDefinitionRepository

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/agent-definitions", tags=["Agent Definitions"])


# ── Request / Response models ────────────────────────────────────

class AgentDefinitionCreate(BaseModel):
    agent_id: str
    name: str
    description: Optional[str] = None
    role: Optional[str] = None
    expertise: Optional[str] = None
    task_requirements: Optional[str] = None
    system_prompt: str
    domain_tools: List[str] = []
    core_tools_enabled: bool = True
    skills: List[Dict[str, Any]] = []
    is_enabled: bool = True
    version: str = "1.0.0"
    icon: Optional[str] = None
    settings: Dict[str, Any] = {}


class AgentDefinitionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    role: Optional[str] = None
    expertise: Optional[str] = None
    task_requirements: Optional[str] = None
    system_prompt: Optional[str] = None
    domain_tools: Optional[List[str]] = None
    core_tools_enabled: Optional[bool] = None
    skills: Optional[List[Dict[str, Any]]] = None
    is_enabled: Optional[bool] = None
    version: Optional[str] = None
    icon: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    changed_by: Optional[str] = None
    change_reason: Optional[str] = None


class RestoreVersionRequest(BaseModel):
    changed_by: Optional[str] = None


# ── Fixed-path endpoints (MUST be before parametric /{agent_id}) ──

@router.post("/reload")
async def reload_agents():
    """Hot-reload: recarga el registry de agentes desde BD."""
    count = await _reload_registry()
    return {"status": "reloaded", "agents_loaded": count}


@router.get("/meta/available-tools")
async def list_available_tools():
    """Lista todas las tools disponibles en el registry (para selector de GUI)."""
    from src.tools import tool_registry
    tools = tool_registry.list()
    return {
        "tools": [
            {"id": t.id, "name": t.name, "description": t.description}
            for t in tools
        ],
        "total": len(tools),
    }


# ── CRUD endpoints ───────────────────────────────────────────────

@router.get("")
async def list_agent_definitions():
    definitions = await AgentDefinitionRepository.get_all()
    return {
        "definitions": [d.model_dump(mode="json") for d in definitions],
        "total": len(definitions),
    }


@router.get("/{agent_id}")
async def get_agent_definition(agent_id: str):
    defn = await AgentDefinitionRepository.get_by_agent_id(agent_id)
    if not defn:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return defn.model_dump(mode="json")


@router.post("", status_code=201)
async def create_agent_definition(body: AgentDefinitionCreate):
    existing = await AgentDefinitionRepository.get_by_agent_id(body.agent_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Agent '{body.agent_id}' already exists")

    defn = await AgentDefinitionRepository.create(body.model_dump())
    await _reload_registry()
    return defn.model_dump(mode="json")


@router.put("/{agent_id}")
async def update_agent_definition(agent_id: str, body: AgentDefinitionUpdate):
    data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not data:
        raise HTTPException(status_code=400, detail="No fields to update")

    defn = await AgentDefinitionRepository.update(agent_id, data)
    if not defn:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    await _reload_registry()
    return defn.model_dump(mode="json")


@router.delete("/{agent_id}")
async def delete_agent_definition(agent_id: str):
    existing = await AgentDefinitionRepository.get_by_agent_id(agent_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    await AgentDefinitionRepository.delete(agent_id)
    await _reload_registry()
    return {"status": "deleted", "agent_id": agent_id}


# ── Versioning endpoints ─────────────────────────────────────────

@router.get("/{agent_id}/versions")
async def list_agent_versions(agent_id: str):
    versions = await AgentDefinitionRepository.get_versions(agent_id)
    return {
        "agent_id": agent_id,
        "versions": [v.model_dump(mode="json") for v in versions],
        "total": len(versions),
    }


@router.post("/{agent_id}/restore/{version_number}")
async def restore_agent_version(agent_id: str, version_number: int, body: Optional[RestoreVersionRequest] = None):
    defn = await AgentDefinitionRepository.restore_version(agent_id, version_number)
    if not defn:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' or version {version_number} not found")

    await _reload_registry()
    return {
        "status": "restored",
        "agent_id": agent_id,
        "version_restored": version_number,
        "definition": defn.model_dump(mode="json"),
    }


# ── Helpers ───────────────────────────────────────────────────────

async def _reload_registry() -> int:
    from src.engine.chains.agents import reload_subagents
    return await reload_subagents()
