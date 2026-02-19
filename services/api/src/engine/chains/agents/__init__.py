"""
Brain Subagentes — cargados desde BD (tabla agent_definitions).

Al arrancar se hace seed si la tabla esta vacia y se registran
todos los agentes habilitados en el SubAgentRegistry.
"""

import structlog

from .base import BaseSubAgent, SubAgentResult, Skill, SubAgentRegistry, subagent_registry

logger = structlog.get_logger(__name__)


async def register_all_subagents() -> None:
    """Carga agentes desde BD y los registra. Seed si tabla vacia."""
    if subagent_registry.is_initialized():
        return

    from src.db.repositories.agent_definitions import AgentDefinitionRepository
    from .seed import seed_default_agents

    try:
        await seed_default_agents()

        definitions = await AgentDefinitionRepository.get_all_enabled()
        for defn in definitions:
            agent = BaseSubAgent.from_definition(defn)
            subagent_registry.register(agent)

        logger.info("Subagents loaded from DB", count=len(definitions))
    except Exception as e:
        logger.error(f"Failed to load subagents from DB: {e}", exc_info=True)


async def reload_subagents() -> int:
    """Hot-reload: recarga todos los agentes desde BD sin restart."""
    from src.db.repositories.agent_definitions import AgentDefinitionRepository

    subagent_registry.clear()
    definitions = await AgentDefinitionRepository.get_all_enabled()
    for defn in definitions:
        agent = BaseSubAgent.from_definition(defn)
        subagent_registry.register(agent)
    logger.info("Subagents reloaded from DB", count=len(definitions))
    return len(definitions)


__all__ = [
    "BaseSubAgent",
    "SubAgentResult",
    "Skill",
    "SubAgentRegistry",
    "subagent_registry",
    "register_all_subagents",
    "reload_subagents",
]
