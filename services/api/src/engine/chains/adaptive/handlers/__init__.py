"""
Handlers para diferentes tipos de tools.

Cada handler encapsula la lógica específica de una tool o grupo de tools.
"""

from .base import ToolHandler, ToolResult
from .finish import FinishHandler
from .delegate import DelegateHandler
from .parallel_delegate import ParallelDelegateHandler
from .reasoning import ReasoningHandler
from .consult_team import ConsultTeamMemberHandler

# SlidesHandler ya no se usa en el adaptive agent
# Las presentaciones se manejan via delegate → slides_agent


# Mapeo de tool_name -> Handler class
HANDLER_REGISTRY = {
    "finish": FinishHandler,
    "delegate": DelegateHandler,
    "parallel_delegate": ParallelDelegateHandler,
    "consult_team_member": ConsultTeamMemberHandler,
    # generate_slides removido - usar delegate(agent="slides_agent", ...)
    "think": ReasoningHandler,
    "reflect": ReasoningHandler,
    "plan": ReasoningHandler,
}


def get_handler(tool_name: str) -> type[ToolHandler] | None:
    """
    Obtiene la clase de handler para una tool.
    
    Args:
        tool_name: Nombre de la tool
        
    Returns:
        Clase del handler o None si no hay handler especial
    """
    return HANDLER_REGISTRY.get(tool_name)


__all__ = [
    "ToolHandler",
    "ToolResult",
    "FinishHandler",
    "DelegateHandler",
    "ParallelDelegateHandler",
    "ConsultTeamMemberHandler",
    "ReasoningHandler",
    "get_handler",
    "HANDLER_REGISTRY",
]
