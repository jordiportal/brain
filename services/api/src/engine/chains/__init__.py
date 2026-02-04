"""
Brain 2.0 Chains Module

Cadenas disponibles:
- adaptive: Agente principal con herramientas y subagentes (respuesta rápida)
- team: Equipo de agentes con consenso (respuesta elaborada)

Estructura del módulo adaptive (refactorizado v2.1.0):
- adaptive/prompts/: System prompts por proveedor
- adaptive/handlers/: Handlers para diferentes tools
- adaptive/events/: Emisores de eventos
- adaptive/validators.py: Validación
- adaptive/executor.py: Loop principal
- adaptive/agent.py: Builder y definición

Estructura del módulo team:
- team/coordinator.py: build_team_coordinator (AdaptiveExecutor + consult_team_member)
- team/prompts.py: COORDINATOR_SYSTEM_PROMPT
"""

# Import desde el nuevo paquete refactorizado
from .adaptive import register_adaptive_agent
from .team import register_team_chain


def register_all_chains():
    """Registrar todas las cadenas de Brain 2.0"""
    register_adaptive_agent()
    register_team_chain()
