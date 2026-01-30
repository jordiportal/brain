"""
Brain 2.0 Chains Module

Cadenas disponibles:
- adaptive: Agente principal con herramientas y subagentes (incluye slides_agent)
- conversational: Chat simple (para OpenAI-compat brain-chat)
- rag: Chat con búsqueda de documentos (para OpenAI-compat brain-rag)

Nota: La generación de presentaciones se hace vía adaptive_agent → delegate → slides_agent
"""

from .adaptive_agent import register_adaptive_agent
from .conversational import register_conversational_chain
from .rag_chain import register_rag_chain


def register_all_chains():
    """Registrar todas las cadenas de Brain 2.0"""
    register_adaptive_agent()
    register_conversational_chain()
    register_rag_chain()
