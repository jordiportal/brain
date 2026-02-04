"""
Brain 2.0 Adaptive Agent (v2.1.0)

Agente principal con razonamiento adaptativo y 17+ core tools.

Estructura:
    adaptive/
    ├── agent.py         # Builder + ChainDefinition
    ├── executor.py      # Loop de ejecución
    ├── validators.py    # Validación
    ├── prompts/         # Prompts por proveedor
    ├── handlers/        # Handlers de tools
    └── events/          # Emisores de eventos

Uso:
    from src.engine.chains.adaptive import build_adaptive_agent
    
    async for event in build_adaptive_agent(config, llm_url, model, ...):
        print(event)

Ver README.md para documentación completa.
"""

from .agent import (
    build_adaptive_agent,
    register_adaptive_agent,
    ADAPTIVE_AGENT_DEFINITION,
)

__all__ = [
    "build_adaptive_agent",
    "register_adaptive_agent",
    "ADAPTIVE_AGENT_DEFINITION",
]
