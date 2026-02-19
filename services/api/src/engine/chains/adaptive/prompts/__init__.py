"""
Prompts del Adaptive Agent organizados por proveedor LLM.

Cada proveedor tiene características diferentes y responde mejor
a estilos de prompt específicos.
"""

from datetime import datetime

from .base import (
    TOOLS_SECTION,
    SUBAGENTS_SECTION,
    WORKFLOW,
    WORKFLOW_SIMPLE,
    WORKFLOW_MODERATE,
    WORKFLOW_COMPLEX
)
from .ollama import PROMPT_OLLAMA
from .openai import PROMPT_OPENAI
from .anthropic import PROMPT_ANTHROPIC
from .google import PROMPT_GOOGLE


def _date_context() -> str:
    now = datetime.now()
    return (
        f"\n\nFecha actual del sistema: {now.strftime('%A %d de %B de %Y')} "
        f"({now.strftime('%Y-%m-%d')}). Mes: {now.strftime('%Y%m')}. Año: {now.year}.\n"
    )


def get_system_prompt(provider_type: str) -> str:
    """
    Obtiene el system prompt optimizado para el proveedor LLM.
    
    Args:
        provider_type: ollama, openai, anthropic, google, openrouter
    
    Returns:
        Template del prompt (necesita .format(workflow_instructions=...))
    """
    prompts = {
        "ollama": PROMPT_OLLAMA,
        "openai": PROMPT_OPENAI,
        "anthropic": PROMPT_ANTHROPIC,
        "google": PROMPT_GOOGLE,
        "openrouter": PROMPT_OPENAI,
    }
    
    base_prompt = prompts.get(provider_type, PROMPT_OPENAI)
    
    return base_prompt.format(
        tools_section=TOOLS_SECTION,
        subagents_section=SUBAGENTS_SECTION,
        workflow_instructions="{workflow_instructions}",
    ) + _date_context()


def get_workflow(complexity: str = "normal") -> str:
    """
    Obtiene las instrucciones de workflow.
    
    El LLM decide qué herramientas usar - workflow único.
    
    Args:
        complexity: Ignorado (mantenido por compatibilidad)
    
    Returns:
        Instrucciones de workflow
    """
    return WORKFLOW


__all__ = [
    "get_system_prompt",
    "get_workflow",
    "TOOLS_SECTION",
    "SUBAGENTS_SECTION",
    "WORKFLOW",
]
