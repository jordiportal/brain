"""
Brain 2.0 Chains Module

Cadenas disponibles:
- adaptive: Agente principal con herramientas y subagentes (respuesta rápida)
- team: Equipo de agentes con consenso (respuesta elaborada)
- conversational: Chat simple (para OpenAI-compat brain-chat)
- rag: Chat con búsqueda de documentos (para OpenAI-compat brain-rag)

Estructura del módulo adaptive (refactorizado v2.1.0):
- adaptive/prompts/: System prompts por proveedor
- adaptive/handlers/: Handlers para diferentes tools
- adaptive/events/: Emisores de eventos
- adaptive/validators.py: Validación
- adaptive/executor.py: Loop principal
- adaptive/agent.py: Builder y definición

Estructura del módulo team:
- team/coordinator.py: TeamCoordinator principal
- team/consensus.py: Motor de consenso
- team/prompts.py: Prompts de coordinación
"""

# Import desde el nuevo paquete refactorizado
from .adaptive import register_adaptive_agent
from .conversational import register_conversational_chain
from .rag_chain import register_rag_chain
from .team import register_team_chain


def register_all_chains():
    """Registrar todas las cadenas de Brain 2.0"""
    register_adaptive_agent()
    register_team_chain()
    register_conversational_chain()
    register_rag_chain()
