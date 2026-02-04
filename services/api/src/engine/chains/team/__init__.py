"""
Team module - Sistema de equipos con consenso dirigido por LLM.

Cadena brain-team: coordinador usa AdaptiveExecutor con herramientas de cognición
(think, reflect, plan) y consult_team_member para alcanzar consenso.
El system prompt es único: el guardado en la GUI (BD). No hay copia en código.
"""

import structlog

from ...models import ChainDefinition, ChainConfig
from .coordinator import build_team_coordinator

logger = structlog.get_logger()


def register_team_chain():
    """Registra la cadena team en el registry."""
    from ...registry import chain_registry

    definition = ChainDefinition(
        id="team",
        name="Brain Team",
        description="Equipo de agentes con consenso - Respuestas elaboradas mediante colaboración",
        type="agent",  # Usa la misma plantilla de edición que adaptive
        version="1.0.0",
        config=ChainConfig(
            max_iterations=10,
            timeout_seconds=300,  # 5 minutos para trabajo en equipo
            temperature=0.7
        ),
    )

    chain_registry.register(
        chain_id="team",
        definition=definition,
        builder=build_team_coordinator
    )

    logger.info("✅ Brain Team chain registered (v1.0.0)")


__all__ = [
    "register_team_chain",
    "build_team_coordinator"
]
