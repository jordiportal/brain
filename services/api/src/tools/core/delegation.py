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


async def consult_team_member(
    agent: str,
    task: str,
    context: Optional[str] = None,
    _llm_url: Optional[str] = None,
    _model: Optional[str] = None,
    _provider_type: Optional[str] = None,
    _api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Consulta a un miembro del equipo para obtener su opinión o propuesta (sin ejecutar la tarea completa).
    
    Usa esta tool en modo Team para que cada subagente aporte su perspectiva; luego usa think/reflect/plan
    para sintetizar y alcanzar consenso. No ejecuta la tarea final del subagente, solo su "propuesta".
    
    Args:
        agent: ID del subagente (media_agent, slides_agent, analyst_agent, communication_agent)
        task: Pregunta o tema sobre el que quieres la opinión del experto
        context: Contexto adicional (ej. propuestas de otros miembros)
        _llm_url, _model, _provider_type, _api_key: Config LLM (inyectada por el sistema)
    
    Returns:
        Dict con response (texto de la propuesta/opinión), agent_name, success.
    """
    from src.engine.chains.agents import subagent_registry, register_all_subagents
    
    if not subagent_registry.is_initialized():
        register_all_subagents()
    
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
        result = await subagent.consult(
            topic=task,
            context=context,
            llm_url=_llm_url,
            model=_model,
            provider_type=_provider_type or "ollama",
            api_key=_api_key
        )
        return {
            "success": result.success,
            "response": result.response,
            "agent_id": result.agent_id,
            "agent_name": result.agent_name,
            "data": result.data,
            "error": result.error
        }
    except Exception as e:
        logger.error(f"Consult team member error: {e}", agent=agent, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "agent": agent,
            "agent_name": getattr(subagent, "name", agent)
        }


async def get_agent_info(agent: str) -> Dict[str, Any]:
    """
    Obtiene información sobre un subagente, incluyendo su rol, expertise y qué datos necesita.
    
    Usa esta tool ANTES de delegar para:
    1. Conocer el rol profesional del subagente
    2. Saber en qué puede ayudarte (expertise)
    3. Entender qué formato de datos necesita
    
    Args:
        agent: ID del subagente (media_agent, slides_agent, etc.)
    
    Returns:
        Dict con información completa del subagente
    """
    from src.engine.chains.agents import subagent_registry, register_all_subagents
    
    if not subagent_registry.is_initialized():
        register_all_subagents()
    
    subagent = subagent_registry.get(agent)
    
    if not subagent:
        available = subagent_registry.list_ids()
        return {
            "success": False,
            "error": f"Subagente '{agent}' no encontrado",
            "available_agents": available
        }
    
    return {
        "success": True,
        "id": subagent.id,
        "name": subagent.name,
        "role": getattr(subagent, 'role', 'Especialista'),
        "expertise": getattr(subagent, 'expertise', subagent.description),
        "task_requirements": subagent.task_requirements,
        "supports_consult_mode": True,  # Todos los subagentes ahora soportan consulta
        "version": subagent.version
    }


# ============================================
# Tool Definitions
# ============================================

GET_AGENT_INFO_TOOL = {
    "id": "get_agent_info",
    "name": "get_agent_info",
    "description": """Obtiene información sobre un subagente, incluyendo qué datos necesita.

Usa esta tool ANTES de delegar para saber exactamente qué formato de datos
espera el subagente. Cada subagente tiene requisitos específicos.

Subagentes disponibles:
- media_agent: Generación de imágenes
- slides_agent: Generación de presentaciones""",
    "parameters": {
        "type": "object",
        "properties": {
            "agent": {
                "type": "string",
                "enum": ["media_agent", "slides_agent"],
                "description": "ID del subagente"
            }
        },
        "required": ["agent"]
    },
    "handler": get_agent_info
}


DELEGATE_TOOL = {
    "id": "delegate",
    "name": "delegate",
    "description": """Delega una tarea a un subagente especializado.

Usa esta tool cuando la tarea requiere capacidades de un dominio específico.
IMPORTANTE: Usa get_agent_info primero para saber qué formato de datos espera el subagente.""",
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
                "description": "Datos para el subagente (usa get_agent_info para saber el formato)"
            },
            "context": {
                "type": "string",
                "description": "Contexto adicional (opcional)"
            }
        },
        "required": ["agent", "task"]
    },
    "handler": delegate
}


CONSULT_TEAM_MEMBER_TOOL = {
    "id": "consult_team_member",
    "name": "consult_team_member",
    "description": """Consulta a un miembro del equipo para obtener su opinión o propuesta (sin ejecutar la tarea completa).

Usa esta tool en modo Team para que cada experto aporte su perspectiva. Luego usa think/reflect/plan
para sintetizar y alcanzar consenso. No ejecuta la tarea final del subagente, solo obtiene su propuesta.

Miembros disponibles:
- media_agent: Experto en imágenes y arte visual
- slides_agent: Experto en presentaciones y diseño
- communication_agent: Experto en comunicación y narrativa
- analyst_agent: Experto en datos y análisis""",
    "parameters": {
        "type": "object",
        "properties": {
            "agent": {
                "type": "string",
                "enum": ["media_agent", "slides_agent", "communication_agent", "analyst_agent"],
                "description": "ID del miembro del equipo a consultar"
            },
            "task": {
                "type": "string",
                "description": "Pregunta o tema sobre el que quieres la opinión del experto"
            },
            "context": {
                "type": "string",
                "description": "Contexto adicional (ej. propuestas de otros miembros)"
            }
        },
        "required": ["agent", "task"]
    },
    "handler": consult_team_member
}
