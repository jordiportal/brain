"""
Brain 2.0 Tools Module

Exporta el registry de las 15 Core Tools.
"""

from .tool_registry import (
    ToolRegistry,
    ToolDefinition,
    ToolType,
    tool_registry,
    get_tool_registry
)

from .core import CORE_TOOLS


# ============================================
# Compatibilidad con Brain 1.x
# Stubs para imports que ya no existen
# ============================================

def get_available_agents_description() -> str:
    """Stub para compatibilidad - devuelve string vacío en Brain 2.0"""
    return "Brain 2.0 uses a single adaptive agent with 15 core tools."

def delegate_to_agent(**kwargs):
    """Stub para compatibilidad - delegación deshabilitada en Brain 2.0"""
    return {
        "success": False,
        "error": "Agent delegation disabled in Brain 2.0 - use core tools instead"
    }

def get_agents_enum():
    """Stub para compatibilidad - retorna lista vacía en Brain 2.0"""
    return []


__all__ = [
    "ToolRegistry",
    "ToolDefinition", 
    "ToolType",
    "tool_registry",
    "get_tool_registry",
    "CORE_TOOLS",
    # Compatibilidad Brain 1.x
    "get_available_agents_description",
    "delegate_to_agent",
    "get_agents_enum"
]
