"""
Delegation Tool - Permite al Adaptive Agent delegar a subagentes especializados

Esta tool permite al agente principal (Adaptive Agent) delegar tareas
a subagentes especializados por dominio:
- designer_agent: Generación y manipulación de imágenes, vídeos y presentaciones
- researcher_agent: Búsqueda e investigación web
- communication_agent: Estrategia y comunicación
- sap_analyst: Análisis de datos SAP S/4HANA, ECC y BI
"""

import time
from typing import Dict, Any, Optional, Literal

import structlog

logger = structlog.get_logger()


async def _get_subagent_llm_config(agent_id: str, parent_llm_url: Optional[str], 
                                   parent_model: Optional[str], parent_provider_type: Optional[str],
                                   parent_api_key: Optional[str]) -> Dict[str, Optional[str]]:
    """
    Obtiene la configuración LLM para un subagente.
    
    Prioridad:
    1. Configuración guardada en subagent_configs (si existe llm_provider_id)
    2. Configuración del agente padre (heredada)
    3. Error - no hay proveedor disponible
    
    Returns:
        Dict con llm_url, model, provider_type, api_key
    """
    try:
        from src.db.repositories.subagent_configs import SubagentConfigRepository
        from src.db.repositories.llm_providers import LLMProviderRepository
        
        # 1. Buscar config específica del subagente
        subagent_config = await SubagentConfigRepository.get_by_agent_id(agent_id)
        
        if subagent_config and subagent_config.llm_provider_id:
            # El subagente tiene un proveedor configurado
            provider = await LLMProviderRepository.get_by_id(subagent_config.llm_provider_id)
            
            if provider and provider.is_active:
                logger.info(
                    f"Using subagent-specific LLM config",
                    agent_id=agent_id,
                    provider_id=provider.id,
                    provider_name=provider.name,
                    provider_type=provider.type
                )
                return {
                    "llm_url": provider.base_url,
                    "model": subagent_config.llm_model or provider.default_model,
                    "provider_type": provider.type,
                    "api_key": provider.api_key
                }
            elif provider:
                logger.warning(
                    f"Subagent LLM provider is inactive",
                    agent_id=agent_id,
                    provider_id=provider.id,
                    provider_name=provider.name
                )
        
        # 2. Si no hay config específica, usar la del padre (si existe y tiene provider_type)
        if parent_llm_url and parent_provider_type:
            logger.info(
                f"Using parent LLM config for subagent",
                agent_id=agent_id,
                parent_url=parent_llm_url,
                parent_provider=parent_provider_type
            )
            return {
                "llm_url": parent_llm_url,
                "model": parent_model,
                "provider_type": parent_provider_type,
                "api_key": parent_api_key
            }
        
        # 3. No hay configuración disponible
        logger.error(
            f"No LLM configuration available for subagent",
            agent_id=agent_id,
            has_parent_config=bool(parent_llm_url),
            has_subagent_config=bool(subagent_config and subagent_config.llm_provider_id)
        )
        
        raise ValueError(
            f"No hay configuración LLM disponible para el subagente '{agent_id}'. "
            f"Configure un proveedor LLM para este subagente en la sección de Configuración."
        )
        
    except Exception as e:
        logger.error(f"Error resolving subagent LLM config: {e}", agent_id=agent_id)
        # Si hay error en la BD, intentar usar la del padre como fallback
        if parent_llm_url:
            return {
                "llm_url": parent_llm_url,
                "model": parent_model,
                "provider_type": parent_provider_type,
                "api_key": parent_api_key
            }
        raise


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
        # Obtener configuración LLM del subagente (o heredar del padre)
        llm_config = await _get_subagent_llm_config(
            agent, _llm_url, _model, _provider_type, _api_key
        )
        
        # Ejecutar el subagente con su configuración específica
        result = await subagent.execute(
            task=task,
            context=context,
            llm_url=llm_config["llm_url"],
            model=llm_config["model"],
            provider_type=llm_config["provider_type"],
            api_key=llm_config["api_key"]
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
        # Obtener configuración LLM del subagente (o heredar del padre)
        llm_config = await _get_subagent_llm_config(
            agent, _llm_url, _model, _provider_type, _api_key
        )
        
        result = await subagent.consult(
            topic=task,
            context=context,
            llm_url=llm_config["llm_url"],
            model=llm_config["model"],
            provider_type=llm_config["provider_type"],
            api_key=llm_config["api_key"]
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

def _get_agent_ids() -> list:
    """Obtiene IDs de subagentes registrados (enum dinámico)."""
    try:
        from src.engine.chains.agents import subagent_registry, register_all_subagents
        if not subagent_registry.is_initialized():
            register_all_subagents()
        return subagent_registry.list_ids()
    except Exception:
        return ["designer_agent", "researcher_agent", "communication_agent"]


def get_agent_info_tool() -> dict:
    """Tool get_agent_info con enum dinámico."""
    return {
        "id": "get_agent_info",
        "name": "get_agent_info",
        "description": """Obtiene información sobre un subagente (rol, expertise, formato de datos).

Usa ANTES de delegar para saber qué espera cada subagente.""",
        "parameters": {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "enum": _get_agent_ids(),
                    "description": "ID del subagente"
                }
            },
            "required": ["agent"]
        },
        "handler": get_agent_info
    }


def get_delegate_tool() -> dict:
    """Tool delegate con enum dinámico."""
    return {
        "id": "delegate",
        "name": "delegate",
        "description": """Delega una tarea a un subagente. Usa get_agent_info primero si no conoces el formato.

- designer_agent: Imágenes, vídeos cinematográficos y presentaciones
- researcher_agent: Búsqueda web (datos actuales)
- communication_agent: Estrategia y narrativa
- sap_analyst: Análisis de datos SAP (FI/CO, SD, MM, PP, HR)""",
        "parameters": {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "enum": _get_agent_ids(),
                    "description": "ID del subagente"
                },
                "task": {
                    "type": "string",
                    "description": "Tarea para el subagente"
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


def get_consult_team_member_tool() -> dict:
    """Tool consult_team_member con enum dinámico."""
    return {
        "id": "consult_team_member",
        "name": "consult_team_member",
        "description": """Consulta a un miembro del equipo (obtiene opinión, no ejecuta).

Usa think/reflect/plan para sintetizar las propuestas.""",
        "parameters": {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "enum": _get_agent_ids(),
                    "description": "ID del miembro"
                },
                "task": {
                    "type": "string",
                    "description": "Pregunta o tema"
                },
                "context": {
                    "type": "string",
                    "description": "Contexto adicional"
                }
            },
            "required": ["agent", "task"]
        },
        "handler": consult_team_member
    }


