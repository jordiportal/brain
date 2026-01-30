"""
Brain 2.0 Reasoning Modes (Simplified)

El LLM decide qué herramientas usar basándose en el prompt.
Solo se distingue entre casos TRIVIALES (respuesta directa) y NORMAL (LLM decide).
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
import structlog

from .complexity import ComplexityLevel

logger = structlog.get_logger()


class ReasoningMode(str, Enum):
    """Modos de razonamiento disponibles"""
    NONE = "none"           # Sin tools (solo para triviales)
    STANDARD = "standard"   # El LLM decide qué hacer


@dataclass
class ReasoningConfig:
    """Configuración de razonamiento"""
    mode: ReasoningMode
    max_iterations: int     # Máximo de iteraciones del loop
    temperature: float      # Temperatura del LLM
    description: str


# Configuraciones por modo
REASONING_CONFIGS = {
    ReasoningMode.NONE: ReasoningConfig(
        mode=ReasoningMode.NONE,
        max_iterations=1,
        temperature=0.7,
        description="Respuesta directa sin herramientas (triviales)"
    ),
    
    ReasoningMode.STANDARD: ReasoningConfig(
        mode=ReasoningMode.STANDARD,
        max_iterations=15,
        temperature=0.5,
        description="El LLM decide qué herramientas usar"
    ),
}


# Mapeo de complejidad a modo
COMPLEXITY_TO_MODE = {
    ComplexityLevel.TRIVIAL: ReasoningMode.NONE,
    ComplexityLevel.NORMAL: ReasoningMode.STANDARD,
}


def get_reasoning_config(
    complexity: ComplexityLevel,
    force_mode: Optional[ReasoningMode] = None
) -> ReasoningConfig:
    """
    Obtiene la configuración de razonamiento.
    
    Args:
        complexity: Nivel de complejidad (TRIVIAL o NORMAL)
        force_mode: Modo forzado (opcional)
    
    Returns:
        ReasoningConfig
    """
    if force_mode:
        mode = force_mode
    else:
        mode = COMPLEXITY_TO_MODE.get(complexity, ReasoningMode.STANDARD)
    
    config = REASONING_CONFIGS[mode]
    
    logger.debug(
        f"📐 Reasoning config: {mode.value}",
        max_iterations=config.max_iterations
    )
    
    return config
