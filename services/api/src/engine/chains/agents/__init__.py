"""
Brain 2.0 Subagentes Especializados (v2.0.0)

Subagentes de dominio invocables via `delegate` desde el Adaptive Agent.

Estructura:
    agents/
    ├── base.py          # BaseSubAgent + Registry
    ├── media/           # Generación de imágenes (DALL-E, SD, Flux)
    ├── slides/          # Presentaciones HTML con Brain Events
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


def register_all_subagents():
    """Registra todos los subagentes en el registry."""
    if not subagent_registry.is_initialized():
        subagent_registry.register(MediaAgent())
        subagent_registry.register(SlidesAgent())


__all__ = [
    "BaseSubAgent",
    "SubAgentResult",
    "SubAgentRegistry",
    "subagent_registry",
    "MediaAgent",
    "SlidesAgent",
    "register_all_subagents"
]
