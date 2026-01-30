"""
Handlers para diferentes tipos de tools.

Cada handler encapsula la lógica específica de una tool o grupo de tools.
"""

from .base import ToolHandler, ToolResult
from .finish import FinishHandler
from .delegate import DelegateHandler
from .slides import SlidesHandler
from .reasoning import ReasoningHandler


# Mapeo de tool_name -> Handler class
HANDLER_REGISTRY = {
    "finish": FinishHandler,
    "delegate": DelegateHandler,
    "generate_slides": SlidesHandler,
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
    "SlidesHandler",
    "ReasoningHandler",
    "get_handler",
    "HANDLER_REGISTRY",
]
