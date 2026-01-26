"""
Brain 2.0 Complexity Detector

Analiza queries del usuario para determinar el nivel de complejidad
y el modo de razonamiento apropiado.
"""

import re
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Set
import structlog

logger = structlog.get_logger()


class ComplexityLevel(str, Enum):
    """Niveles de complejidad de tareas"""
    TRIVIAL = "trivial"      # Respuesta directa, sin tools
    SIMPLE = "simple"        # 1-2 tools, secuencial
    MODERATE = "moderate"    # 3-5 tools, posible ramificación
    COMPLEX = "complex"      # 6+ tools, múltiples fuentes


@dataclass
class ComplexityAnalysis:
    """Resultado del análisis de complejidad"""
    level: ComplexityLevel
    estimated_tools: int
    reasoning_needed: bool
    keywords_found: List[str]
    confidence: float
    explanation: str


# Keywords que indican diferentes niveles de complejidad
TRIVIAL_PATTERNS = [
    r"^hola\b",
    r"^hi\b",
    r"^qué hora es",
    r"^cuánto es \d+",
    r"^gracias\b",
    r"^ok\b",
    r"^entendido\b",
]

SIMPLE_INDICATORS = {
    "lee", "leer", "read", "muestra", "show",
    "calcula", "calculate", "suma", "resta",
    "busca", "search", "encuentra", "find",
    "lista", "list", "ejecuta", "run",
}

MODERATE_INDICATORS = {
    "edita", "edit", "modifica", "modify", "cambia", "change",
    "crea", "create", "escribe", "write", "genera", "generate",
    "analiza", "analyze", "compara", "compare",
    "descarga", "download", "obtén", "fetch", "get",
    "instala", "install", "configura", "configure",
}

COMPLEX_INDICATORS = {
    "refactoriza", "refactor", "migra", "migrate",
    "implementa", "implement", "desarrolla", "develop",
    "integra", "integrate", "despliega", "deploy",
    "optimiza", "optimize", "documenta", "document",
    "automatiza", "automate", "monitorea", "monitor",
    "investiga", "investigate", "explora", "explore",
    "proyecto", "project", "aplicación", "application",
    "sistema", "system", "arquitectura", "architecture",
}

# Palabras que sugieren múltiples pasos
MULTI_STEP_WORDS = {
    "y luego", "después", "then", "and then",
    "primero", "segundo", "tercero", "first", "second", "third",
    "paso", "step", "pasos", "steps",
    "proceso", "process", "workflow",
    "todos los", "all the", "cada", "each",
    "múltiples", "multiple", "varios", "several",
}


def detect_complexity(
    query: str,
    available_tools: Optional[List[str]] = None
) -> ComplexityAnalysis:
    """
    Analiza una query para determinar su complejidad.
    
    Args:
        query: Texto de la consulta del usuario
        available_tools: Lista de herramientas disponibles (opcional)
    
    Returns:
        ComplexityAnalysis con el nivel detectado y metadata
    """
    query_lower = query.lower().strip()
    keywords_found = []
    
    # Verificar patrones triviales
    for pattern in TRIVIAL_PATTERNS:
        if re.search(pattern, query_lower):
            return ComplexityAnalysis(
                level=ComplexityLevel.TRIVIAL,
                estimated_tools=0,
                reasoning_needed=False,
                keywords_found=[],
                confidence=0.9,
                explanation="Query simple que puede responderse directamente"
            )
    
    # Contar indicadores de cada nivel
    simple_count = sum(1 for word in SIMPLE_INDICATORS if word in query_lower)
    moderate_count = sum(1 for word in MODERATE_INDICATORS if word in query_lower)
    complex_count = sum(1 for word in COMPLEX_INDICATORS if word in query_lower)
    multi_step_count = sum(1 for phrase in MULTI_STEP_WORDS if phrase in query_lower)
    
    # Recopilar keywords encontrados
    for word in SIMPLE_INDICATORS:
        if word in query_lower:
            keywords_found.append(word)
    for word in MODERATE_INDICATORS:
        if word in query_lower:
            keywords_found.append(word)
    for word in COMPLEX_INDICATORS:
        if word in query_lower:
            keywords_found.append(word)
    
    # Factores adicionales
    query_length = len(query)
    has_code = "```" in query or "def " in query or "function " in query
    has_urls = "http://" in query or "https://" in query
    question_marks = query.count("?")
    
    # Calcular puntuación de complejidad
    complexity_score = (
        simple_count * 1 +
        moderate_count * 2 +
        complex_count * 3 +
        multi_step_count * 2 +
        (1 if has_code else 0) +
        (1 if has_urls else 0) +
        (query_length // 200)  # Queries largas tienden a ser más complejas
    )
    
    # Determinar nivel basado en puntuación
    if complexity_score <= 1:
        if simple_count > 0:
            level = ComplexityLevel.SIMPLE
            estimated_tools = 1
        else:
            level = ComplexityLevel.TRIVIAL
            estimated_tools = 0
    elif complexity_score <= 3:
        level = ComplexityLevel.SIMPLE
        estimated_tools = min(2, simple_count + moderate_count + 1)
    elif complexity_score <= 6:
        level = ComplexityLevel.MODERATE
        estimated_tools = min(5, complexity_score)
    else:
        level = ComplexityLevel.COMPLEX
        estimated_tools = min(10, complexity_score)
    
    # Ajustar por multi-step
    if multi_step_count >= 2:
        if level == ComplexityLevel.SIMPLE:
            level = ComplexityLevel.MODERATE
        elif level == ComplexityLevel.MODERATE:
            level = ComplexityLevel.COMPLEX
    
    # Determinar si necesita razonamiento explícito
    reasoning_needed = level in (ComplexityLevel.MODERATE, ComplexityLevel.COMPLEX)
    
    # Calcular confianza
    if keywords_found:
        confidence = min(0.95, 0.6 + len(keywords_found) * 0.1)
    else:
        confidence = 0.5  # Sin keywords claros, baja confianza
    
    # Generar explicación
    explanations = {
        ComplexityLevel.TRIVIAL: "Query trivial que puede responderse sin herramientas",
        ComplexityLevel.SIMPLE: f"Tarea simple que requiere {estimated_tools} herramienta(s)",
        ComplexityLevel.MODERATE: f"Tarea moderada que requiere ~{estimated_tools} herramientas y planificación",
        ComplexityLevel.COMPLEX: f"Tarea compleja que requiere múltiples herramientas y razonamiento extendido"
    }
    
    analysis = ComplexityAnalysis(
        level=level,
        estimated_tools=estimated_tools,
        reasoning_needed=reasoning_needed,
        keywords_found=keywords_found[:10],  # Limitar a 10
        confidence=confidence,
        explanation=explanations[level]
    )
    
    logger.info(
        f"🎯 Complexity detected: {level.value}",
        estimated_tools=estimated_tools,
        reasoning_needed=reasoning_needed,
        confidence=f"{confidence:.0%}",
        keywords=keywords_found[:5]
    )
    
    return analysis
