"""
Brain 2.0 Specialized Subagents

Subagentes especializados por dominio:
- MediaAgent: Generación y manipulación de imágenes
- SlidesAgent: Generación de presentaciones HTML
- SAPAgent: Integración con SAP S/4HANA y BIW (futuro)
- MailAgent: Gestión de correo electrónico (futuro)
- OfficeAgent: Creación de documentos Office (futuro)
"""

from .base_agent import BaseSubAgent, SubAgentResult, SubAgentRegistry, subagent_registry
from .media_agent import MediaAgent
from .slides_agent import SlidesAgent

# Registrar subagentes disponibles
def register_all_subagents():
    """Registra todos los subagentes en el registry."""
    subagent_registry.register(MediaAgent())
    subagent_registry.register(SlidesAgent())
    # Futuros subagentes:
    # subagent_registry.register(SAPAgent())
    # subagent_registry.register(MailAgent())
    # subagent_registry.register(OfficeAgent())

__all__ = [
    "BaseSubAgent",
    "SubAgentResult", 
    "SubAgentRegistry",
    "subagent_registry",
    "MediaAgent",
    "SlidesAgent",
    "register_all_subagents"
]
