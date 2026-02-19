"""
Team module - Sistema de equipos con consenso dirigido por LLM.

Cadena brain-team: coordinador usa AdaptiveExecutor con herramientas de cognición
(think, reflect, plan) y consult_team_member para alcanzar consenso.
La definición se carga de BD; aquí solo vive el builder.
"""

from .coordinator import build_team_coordinator

__all__ = [
    "build_team_coordinator",
]
