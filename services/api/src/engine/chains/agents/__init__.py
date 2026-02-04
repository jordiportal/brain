"""
Brain 2.0 Subagentes por Rol Profesional (v3.0.0)

Subagentes invocables via delegate desde Adaptive Agent o Team.

Estructura: designer (imágenes+presentaciones), researcher (web), strategist (comunicación).
"""

from .base import BaseSubAgent, SubAgentResult, SubAgentRegistry, subagent_registry
from .designer import DesignerAgent
from .researcher import ResearcherAgent
from .communication import CommunicationAgent


def register_all_subagents():
    """Registra todos los subagentes en el registry."""
    if not subagent_registry.is_initialized():
        subagent_registry.register(DesignerAgent())
        subagent_registry.register(ResearcherAgent())
        subagent_registry.register(CommunicationAgent())


__all__ = [
    "BaseSubAgent",
    "SubAgentResult",
    "SubAgentRegistry",
    "subagent_registry",
    "DesignerAgent",
    "ResearcherAgent",
    "CommunicationAgent",
    "register_all_subagents"
]
