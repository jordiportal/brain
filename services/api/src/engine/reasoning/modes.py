"""
Brain 2.0 Reasoning Modes

Define los modos de razonamiento y sus configuraciones.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
import structlog

from .complexity import ComplexityLevel

logger = structlog.get_logger()


class ReasoningMode(str, Enum):
    """Modos de razonamiento disponibles"""
    NONE = "none"           # Sin razonamiento explícito
    INTERNAL = "internal"   # Razonamiento interno (thinking budget moderado)
    EXTENDED = "extended"   # Razonamiento extendido (thinking budget alto)
    EXPLICIT = "explicit"   # Meta-tools obligatorias (debugging/auditoría)


@dataclass
class ReasoningConfig:
    """Configuración de un modo de razonamiento"""
    mode: ReasoningMode
    thinking_budget: int          # Tokens para thinking interno
    require_think: bool           # Si debe usar tool think
    require_plan: bool            # Si debe usar tool plan
    require_reflect: bool         # Si debe usar tool reflect
    max_iterations: int           # Máximo de iteraciones del loop
    temperature: float            # Temperatura del LLM
    description: str


# Configuraciones por modo
# NOTA: max_iterations aumentados para dar margen al agente de completar tareas multi-step
REASONING_CONFIGS = {
    ReasoningMode.NONE: ReasoningConfig(
        mode=ReasoningMode.NONE,
        thinking_budget=0,
        require_think=False,
        require_plan=False,
        require_reflect=False,
        max_iterations=5,       # Aumentado de 3 a 5
        temperature=0.7,
        description="Respuesta directa sin razonamiento explícito"
    ),
    
    ReasoningMode.INTERNAL: ReasoningConfig(
        mode=ReasoningMode.INTERNAL,
        thinking_budget=5000,
        require_think=False,
        require_plan=False,
        require_reflect=False,
        max_iterations=8,       # Aumentado de 5 a 8
        temperature=0.5,
        description="Razonamiento interno con budget moderado"
    ),
    
    ReasoningMode.EXTENDED: ReasoningConfig(
        mode=ReasoningMode.EXTENDED,
        thinking_budget=10000,
        require_think=True,
        require_plan=True,
        require_reflect=True,
        max_iterations=15,      # Aumentado de 10 a 15
        temperature=0.3,
        description="Razonamiento extendido con planificación"
    ),
    
    ReasoningMode.EXPLICIT: ReasoningConfig(
        mode=ReasoningMode.EXPLICIT,
        thinking_budget=8000,
        require_think=True,
        require_plan=True,
        require_reflect=True,
        max_iterations=12,      # Aumentado de 8 a 12
        temperature=0.3,
        description="Meta-tools obligatorias para debugging"
    )
}


# Mapeo de complejidad a modo de razonamiento
COMPLEXITY_TO_MODE = {
    ComplexityLevel.TRIVIAL: ReasoningMode.NONE,
    ComplexityLevel.SIMPLE: ReasoningMode.NONE,
    ComplexityLevel.MODERATE: ReasoningMode.INTERNAL,
    ComplexityLevel.COMPLEX: ReasoningMode.EXTENDED,
}


def get_reasoning_config(
    complexity: ComplexityLevel,
    force_mode: Optional[ReasoningMode] = None
) -> ReasoningConfig:
    """
    Obtiene la configuración de razonamiento basada en la complejidad.
    
    Args:
        complexity: Nivel de complejidad detectado
        force_mode: Modo forzado (opcional, override automático)
    
    Returns:
        ReasoningConfig con la configuración apropiada
    """
    if force_mode:
        mode = force_mode
    else:
        mode = COMPLEXITY_TO_MODE.get(complexity, ReasoningMode.INTERNAL)
    
    config = REASONING_CONFIGS[mode]
    
    logger.debug(
        f"📐 Reasoning config: {mode.value}",
        thinking_budget=config.thinking_budget,
        max_iterations=config.max_iterations
    )
    
    return config


def should_use_planning(complexity: ComplexityLevel) -> bool:
    """Determina si la tarea requiere planificación explícita"""
    return complexity in (ComplexityLevel.MODERATE, ComplexityLevel.COMPLEX)


def should_use_reflection(complexity: ComplexityLevel) -> bool:
    """Determina si la tarea requiere reflexión después de cada paso"""
    return complexity == ComplexityLevel.COMPLEX
