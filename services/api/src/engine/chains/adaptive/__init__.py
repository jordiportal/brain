"""
Brain 2.0 Adaptive Agent - Refactorizado

Este paquete contiene el agente principal de Brain 2.0 organizado en módulos:

- prompts/: System prompts por proveedor LLM
- handlers/: Handlers para diferentes tipos de tools  
- events/: Emisores de eventos (Stream y Brain Events)
- validators.py: Validación de tools, loops, etc.
- executor.py: Loop principal simplificado
- agent.py: Builder y definición del agente

Uso:
    from .adaptive import build_adaptive_agent, ADAPTIVE_AGENT_DEFINITION
"""

from .agent import (
    build_adaptive_agent,
    register_adaptive_agent,
    ADAPTIVE_AGENT_DEFINITION,
    ADAPTIVE_AGENT_SYSTEM_PROMPT
)

__all__ = [
    "build_adaptive_agent",
    "register_adaptive_agent",
    "ADAPTIVE_AGENT_DEFINITION",
    "ADAPTIVE_AGENT_SYSTEM_PROMPT",
]
