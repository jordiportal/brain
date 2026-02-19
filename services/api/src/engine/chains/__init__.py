"""
Brain 2.0 Chains Module

Cadenas disponibles:
- adaptive: Agente principal con herramientas y subagentes (respuesta rápida)
- team: Equipo de agentes con consenso (respuesta elaborada)

Todas las definiciones se cargan desde la BD al iniciar.
Los builders se resuelven por handler_type.
"""

from .adaptive import build_adaptive_agent
from .team import build_team_coordinator

BUILDER_MAP = {
    "adaptive": build_adaptive_agent,
    "team": build_team_coordinator,
}


def get_builder(handler_type: str | None):
    """Devuelve el builder según handler_type. Por defecto: adaptive."""
    return BUILDER_MAP.get(handler_type or "adaptive", build_adaptive_agent)
