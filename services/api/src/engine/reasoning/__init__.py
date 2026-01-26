"""
Brain 2.0 Reasoning System

Sistema de razonamiento adaptativo que ajusta la profundidad
del pensamiento según la complejidad de la tarea.
"""

from .complexity import (
    ComplexityLevel,
    ComplexityAnalysis,
    detect_complexity
)

from .modes import (
    ReasoningMode,
    get_reasoning_config,
    REASONING_CONFIGS
)

__all__ = [
    "ComplexityLevel",
    "ComplexityAnalysis",
    "detect_complexity",
    "ReasoningMode",
    "get_reasoning_config",
    "REASONING_CONFIGS"
]
