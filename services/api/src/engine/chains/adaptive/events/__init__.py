"""
Módulo de eventos para el Adaptive Agent.

Separa la lógica de emisión de:
- StreamEvents (eventos internos del sistema)
- BrainEvents (markers HTML para Open WebUI)
"""

from .stream_emitter import StreamEmitter
from .brain_emitter import BrainEmitter


__all__ = [
    "StreamEmitter",
    "BrainEmitter",
]
