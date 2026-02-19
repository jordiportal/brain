"""
Brain 2.0 Adaptive Agent (v2.1.0)

Agente principal con razonamiento adaptativo y core tools.
La definición se carga de BD; aquí solo vive el builder.
"""

from .agent import build_adaptive_agent

__all__ = [
    "build_adaptive_agent",
]
