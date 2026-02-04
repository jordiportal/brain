"""
Brain 2.0 Subagentes Especializados (v2.0.0)

Subagentes de dominio invocables via `delegate` desde el Adaptive Agent
o consultados via `consult_team_member` desde el coordinador Brain Team.

Estructura:
    agents/
    ├── base.py          # BaseSubAgent + Registry
    ├── media/           # Generación de imágenes (DALL-E, SD, Flux)
    ├── slides/          # Presentaciones HTML con Brain Events
    ├── communication/   # Estrategia de comunicación y storytelling
    ├── analyst/         # Investigación y análisis de datos
    ├── (futuro) sap/    # Integración SAP S/4HANA
    └── (futuro) mail/   # Gestión de correo

Uso:
    from src.engine.chains.agents import subagent_registry, register_all_subagents
    
    register_all_subagents()
    agent = subagent_registry.get("media_agent")
    result = await agent.execute(task="Genera un logo...")

Ver README.md para documentación completa.
"""

from .base import BaseSubAgent, SubAgentResult, SubAgentRegistry, subagent_registry
from .media import MediaAgent
from .slides import SlidesAgent
from .communication import CommunicationAgent
from .analyst import AnalystAgent


def register_all_subagents():
    """Registra todos los subagentes en el registry."""
    if not subagent_registry.is_initialized():
        # Agentes de ejecución
        subagent_registry.register(MediaAgent())
        subagent_registry.register(SlidesAgent())
        
        # Agentes de equipo (colaboración y análisis)
        subagent_registry.register(CommunicationAgent())
        subagent_registry.register(AnalystAgent())


__all__ = [
    "BaseSubAgent",
    "SubAgentResult",
    "SubAgentRegistry",
    "subagent_registry",
    "MediaAgent",
    "SlidesAgent",
    "CommunicationAgent",
    "AnalystAgent",
    "register_all_subagents"
]
