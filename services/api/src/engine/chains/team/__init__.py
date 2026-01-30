"""
Team module - Sistema de equipos con consenso.

Proporciona una cadena alternativa (brain-team) que coordina
múltiples agentes para resolver tareas complejas mediante debate.
"""

import structlog

from .coordinator import TeamCoordinator, build_team_coordinator
from .consensus import ConsensusEngine, ConsensusResult, Proposal

logger = structlog.get_logger()


def register_team_chain():
    """Registra la cadena team en el registry."""
    from ...registry import chain_registry
    from ...models import ChainDefinition, ChainConfig
    
    definition = ChainDefinition(
        id="team",
        name="Brain Team",
        description="Equipo de agentes con consenso - Respuestas elaboradas mediante colaboración",
        type="team",
        version="1.0.0",
        config=ChainConfig(
            max_iterations=10,
            timeout_seconds=300,  # 5 minutos para trabajo en equipo
            temperature=0.7
        )
    )
    
    chain_registry.register(
        chain_id="team",
        definition=definition,
        builder=build_team_coordinator
    )
    
    logger.info("✅ Brain Team chain registered (v1.0.0)")


__all__ = [
    "TeamCoordinator",
    "ConsensusEngine",
    "ConsensusResult",
    "Proposal",
    "register_team_chain",
    "build_team_coordinator"
]
