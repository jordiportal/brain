"""
Dynamic Agent Card generation from Brain's agent_definitions and chain_registry.

Produces an A2A-compliant AgentCard (Section 4.2) served at
GET /.well-known/agent-card.json
"""

from __future__ import annotations

import logging
from typing import Optional

from src.config import get_settings
from src.db.repositories.agent_definitions import AgentDefinitionRepository
from src.engine.registry import chain_registry

from .models import (
    AgentCard,
    AgentCapabilities,
    AgentInterface,
    AgentProvider,
    AgentSkill,
    SecurityScheme,
    HTTPAuthSecurityScheme,
    APIKeySecurityScheme,
    SecurityRequirement,
)

logger = logging.getLogger(__name__)

A2A_PROTOCOL_VERSION = "1.0"


async def build_agent_card(base_url: Optional[str] = None) -> AgentCard:
    """
    Build the public Agent Card by aggregating:
    - Brain metadata (name, version)
    - Enabled agent_definitions as skills
    - Registered chains as additional skills
    """
    settings = get_settings()
    url = (base_url or "").rstrip("/")
    if not url:
        url = "http://localhost:8000"

    a2a_endpoint = f"{url}/a2a"

    # -- Skills from agent_definitions --
    skills: list[AgentSkill] = []
    try:
        definitions = await AgentDefinitionRepository.get_all_enabled()
        for defn in definitions:
            tags = []
            if defn.role:
                tags.append(defn.role)
            if defn.expertise:
                tags.extend(t.strip() for t in defn.expertise.split(",") if t.strip())
            if not tags:
                tags = ["agent"]

            skills.append(AgentSkill(
                id=defn.agent_id,
                name=defn.name,
                description=defn.description or f"Agent: {defn.name}",
                tags=tags,
                examples=[defn.task_requirements] if defn.task_requirements else [],
            ))
    except Exception as exc:
        logger.warning(f"Could not load agent definitions for Agent Card: {exc}")

    # -- Skills from chain_registry (if not already covered) --
    known_ids = {s.id for s in skills}
    try:
        for chain_def in chain_registry.list_chains():
            if chain_def.id in known_ids:
                continue
            skills.append(AgentSkill(
                id=chain_def.id,
                name=chain_def.name,
                description=chain_def.description or f"Chain: {chain_def.name}",
                tags=["chain", chain_def.type],
            ))
    except Exception as exc:
        logger.warning(f"Could not load chains for Agent Card: {exc}")

    if not skills:
        skills.append(AgentSkill(
            id="brain-default",
            name="Brain Assistant",
            description="General-purpose AI assistant",
            tags=["general", "assistant"],
        ))

    return AgentCard(
        name=settings.app_name,
        description="Brain — AI agent platform with multi-agent orchestration, tool use, RAG, and code execution",
        version=settings.app_version,
        supported_interfaces=[
            AgentInterface(
                url=a2a_endpoint,
                protocol_binding="HTTP+JSON",
                protocol_version=A2A_PROTOCOL_VERSION,
            ),
        ],
        provider=AgentProvider(
            url=url,
            organization="Brain",
        ),
        capabilities=AgentCapabilities(
            streaming=True,
            push_notifications=False,
            extended_agent_card=True,
        ),
        security_schemes={
            "bearer": SecurityScheme(
                http_auth_security_scheme=HTTPAuthSecurityScheme(
                    description="JWT or OAuth Bearer token",
                    scheme="Bearer",
                    bearer_format="JWT",
                ),
            ),
            "apiKey": SecurityScheme(
                api_key_security_scheme=APIKeySecurityScheme(
                    description="Brain API key (sk-brain-*)",
                    location="header",
                    name="Authorization",
                ),
            ),
        },
        security_requirements=[
            SecurityRequirement(schemes={"bearer": []}),
        ],
        default_input_modes=["text/plain", "application/json"],
        default_output_modes=["text/plain", "application/json"],
        skills=skills,
    )
