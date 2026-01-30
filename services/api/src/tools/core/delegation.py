"""
Delegation Tool - Permite al Adaptive Agent delegar a subagentes especializados

Esta tool permite al agente principal (Adaptive Agent) delegar tareas
a subagentes especializados por dominio:
- media_agent: Generación y manipulación de imágenes
- sap_agent: Consultas SAP S/4HANA y BIW (futuro)
- mail_agent: Gestión de correo (futuro)
- office_agent: Documentos Office (futuro)
"""

import time
from typing import Dict, Any, Optional, Literal

import structlog

logger = structlog.get_logger()


async def delegate(
    agent: str,
    task: str,
    context: Optional[str] = None,
    # Contexto LLM heredado del Adaptive Agent
    _llm_url: Optional[str] = None,
    _model: Optional[str] = None,
    _provider_type: Optional[str] = None,
    _api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Delega una tarea a un subagente especializado.
    
    El Adaptive Agent usa esta tool cuando detecta que una tarea
    requiere capacidades especializadas de un dominio específico.
    
    Args:
        agent: ID del subagente (media_agent, sap_agent, mail_agent, office_agent)
        task: Descripción clara de la tarea a realizar
        context: Contexto adicional o resultados de pasos previos
        _llm_url: URL del LLM (inyectada por el sistema)
        _model: Modelo LLM (inyectado por el sistema)
        _provider_type: Tipo de proveedor (inyectado por el sistema)
        _api_key: API key (inyectada por el sistema)
    
    Returns:
        Dict con:
        - success: bool
        - response: Respuesta del subagente
        - agent_name: Nombre del subagente
        - tools_used: Lista de tools usadas
        - images: Lista de imágenes generadas (si aplica)
        - sources: Lista de fuentes (si aplica)
        - error: Mensaje de error (si falló)
    
    Examples:
        # Generar una imagen
        result = await delegate(
            agent="media_agent",
            task="Genera una imagen de un atardecer en la playa"
        )
        
        # Consultar SAP (futuro)
        result = await delegate(
            agent="sap_agent",
            task="Obtener pedidos del día de hoy"
        )
    """
    start_time = time.time()
    
    logger.info(
        "🎯 Delegating to subagent",
        agent=agent,
        task=task[:100],
        has_context=bool(context)
    )
    
    # Importar aquí para evitar circular imports
    from src.engine.chains.agents import subagent_registry, register_all_subagents
    
    # Asegurar que los subagentes estén registrados
    if not subagent_registry.is_initialized():
        register_all_subagents()
    
    # Obtener el subagente
    subagent = subagent_registry.get(agent)
    
    if not subagent:
        available = subagent_registry.list_ids()
        return {
            "success": False,
            "error": f"Subagente '{agent}' no encontrado",
            "available_agents": available,
            "agent": agent
        }
    
    try:
        # Ejecutar el subagente
        result = await subagent.execute(
            task=task,
            context=context,
            llm_url=_llm_url,
            model=_model,
            provider_type=_provider_type,
            api_key=_api_key
        )
        
        execution_time = int((time.time() - start_time) * 1000)
        
        logger.info(
            "✅ Delegation completed",
            agent=agent,
            success=result.success,
            tools_used=result.tools_used,
            has_images=len(result.images) > 0,
            execution_time_ms=execution_time
        )
        
        return result.to_dict()
        
    except Exception as e:
        logger.error(f"❌ Delegation error: {e}", agent=agent, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "agent": agent,
            "execution_time_ms": int((time.time() - start_time) * 1000)
        }


def get_available_subagents_description() -> str:
    """
    Genera descripción de subagentes disponibles para inyectar en prompts.
    
    Returns:
        String con descripción de cada subagente y sus capacidades
    """
    from src.engine.chains.agents import subagent_registry, register_all_subagents
    
    if not subagent_registry.is_initialized():
        register_all_subagents()
    
    return subagent_registry.get_description()


def get_subagent_ids() -> list:
    """
    Obtiene lista de IDs de subagentes disponibles.
    
    Returns:
        Lista de IDs (para enum en schema de tool)
    """
    from src.engine.chains.agents import subagent_registry, register_all_subagents
    
    if not subagent_registry.is_initialized():
        register_all_subagents()
    
    return subagent_registry.list_ids()


# ============================================
# Tool Definition
# ============================================

DELEGATE_TOOL = {
    "id": "delegate",
    "name": "delegate",
    "description": """Delega una tarea a un subagente especializado.

Usa esta tool cuando la tarea requiere capacidades de un dominio específico:
- media_agent: Generación y manipulación de imágenes (DALL-E, Stable Diffusion)
- slides_agent: Generación de presentaciones HTML profesionales
- sap_agent: Consultas a SAP S/4HANA y BIW (próximamente)
- mail_agent: Envío y lectura de emails (próximamente)
- office_agent: Creación de documentos Word, Excel, PowerPoint (próximamente)

El subagente tiene herramientas especializadas y conocimiento del dominio.

IMPORTANTE para slides_agent:
- Primero investiga el tema (web_search si necesario)
- Crea un outline estructurado con: título, slides [{title, type, content/bullets}]
- Pasa el outline como JSON en el campo 'task'
- El slides_agent generará HTML profesional con estilos incluidos""",
    "parameters": {
        "type": "object",
        "properties": {
            "agent": {
                "type": "string",
                "enum": ["media_agent", "slides_agent"],
                "description": "ID del subagente especializado"
            },
            "task": {
                "type": "string",
                "description": "Descripción de la tarea o JSON con outline estructurado (para slides_agent)"
            },
            "context": {
                "type": "string",
                "description": "Contexto adicional: información recopilada, fuentes consultadas, etc."
            }
        },
        "required": ["agent", "task"]
    },
    "handler": delegate
}
