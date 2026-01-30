"""
Brain 2.0 Complexity Detector (Simplified)

Solo detecta casos TRIVIALES (saludos, confirmaciones).
Para el resto de casos, el LLM decide qué herramientas usar
basándose en el prompt.
"""

import re
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional
import structlog

logger = structlog.get_logger()


class ComplexityLevel(str, Enum):
    """Niveles de complejidad de tareas"""
    TRIVIAL = "trivial"    # Respuesta directa, sin tools (saludos, ok, gracias)
    NORMAL = "normal"      # El LLM decide qué hacer


@dataclass
class ComplexityAnalysis:
    """Resultado del análisis de complejidad"""
    level: ComplexityLevel
    is_trivial: bool
    explanation: str


# Patrones que indican casos TRIVIALES (respuesta directa sin tools)
TRIVIAL_PATTERNS = [
    # Saludos
    r"^hola\s*[!.?]?$",
    r"^hi\s*[!.?]?$",
    r"^hey\s*[!.?]?$",
    r"^buenos?\s*(días|tardes|noches)\s*[!.?]?$",
    r"^good\s*(morning|afternoon|evening)\s*[!.?]?$",
    
    # Confirmaciones/agradecimientos
    r"^ok\s*[!.?]?$",
    r"^okay\s*[!.?]?$",
    r"^vale\s*[!.?]?$",
    r"^gracias\s*[!.?]?$",
    r"^thanks\s*[!.?]?$",
    r"^thank\s*you\s*[!.?]?$",
    r"^entendido\s*[!.?]?$",
    r"^perfecto\s*[!.?]?$",
    r"^genial\s*[!.?]?$",
    
    # Despedidas
    r"^adiós\s*[!.?]?$",
    r"^bye\s*[!.?]?$",
    r"^chao\s*[!.?]?$",
    
    # Preguntas triviales sobre el asistente
    r"^quién\s+eres\s*[?]?$",
    r"^cómo\s+te\s+llamas\s*[?]?$",
    r"^who\s+are\s+you\s*[?]?$",
]


def detect_complexity(
    query: str,
    available_tools: Optional[List[str]] = None
) -> ComplexityAnalysis:
    """
    Detecta si una query es TRIVIAL o debe ser procesada por el LLM.
    
    Solo los casos triviales (saludos, confirmaciones) se detectan aquí.
    Para todo lo demás, el LLM decide basándose en el prompt.
    
    Args:
        query: Texto de la consulta del usuario
        available_tools: No usado (mantenido por compatibilidad)
    
    Returns:
        ComplexityAnalysis con is_trivial=True si es un saludo/confirmación
    """
    query_lower = query.lower().strip()
    
    # Verificar patrones triviales
    for pattern in TRIVIAL_PATTERNS:
        if re.search(pattern, query_lower):
            logger.debug(f"🎯 Trivial query detected: '{query[:50]}'")
            return ComplexityAnalysis(
                level=ComplexityLevel.TRIVIAL,
                is_trivial=True,
                explanation="Saludo o confirmación - respuesta directa sin herramientas"
            )
    
    # Para todo lo demás, el LLM decide
    logger.debug(f"🎯 Normal query - LLM will decide: '{query[:50]}'")
    return ComplexityAnalysis(
        level=ComplexityLevel.NORMAL,
        is_trivial=False,
        explanation="El LLM decidirá qué herramientas usar"
    )
