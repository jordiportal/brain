"""
Brain 2.0 Chains Module

Cadenas disponibles:
- adaptive: Agente principal con herramientas y subagentes
- conversational: Chat simple (para OpenAI-compat brain-chat)
- rag: Chat con búsqueda de documentos (para OpenAI-compat brain-rag)
- brain-slides: Generador de presentaciones HTML (para OpenAI-compat brain-slides)
"""

from .adaptive_agent import register_adaptive_agent
from .conversational import register_conversational_chain
from .rag_chain import register_rag_chain
from .slides_chain import register_slides_chain


def register_all_chains():
    """Registrar todas las cadenas de Brain 2.0"""
    register_adaptive_agent()
    register_conversational_chain()
    register_rag_chain()
    register_slides_chain()
