"""
Router para gestión de Subagentes Especializados

Endpoints para listar, configurar y probar subagentes.
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
import structlog

from . import subagent_registry, register_all_subagents

logger = structlog.get_logger()

router = APIRouter(prefix="/subagents", tags=["Subagents"])


class SubagentExecuteRequest(BaseModel):
    """Request para ejecutar una tarea en un subagente"""
    task: str
    context: Optional[str] = None
    llm_url: Optional[str] = None
    model: Optional[str] = None
    provider_type: str = "ollama"
    api_key: Optional[str] = None


class SubagentConfigUpdate(BaseModel):
    """Request para actualizar configuración de un subagente"""
    enabled: bool = True
    system_prompt: Optional[str] = None
    default_provider: Optional[str] = None
    default_model: Optional[str] = None
    settings: Dict[str, Any] = {}


# ============================================
# Listar y Obtener Subagentes
# ============================================

@router.get("")
async def list_subagents():
    """Lista todos los subagentes registrados"""
    # Asegurar que los subagentes estén registrados
    if not subagent_registry.is_initialized():
        register_all_subagents()
    
    agents = subagent_registry.list()
    
    return {
        "subagents": [
            {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "version": agent.version,
                "domain_tools": agent.domain_tools,
                "status": "active",  # TODO: Cargar desde config
                "icon": _get_agent_icon(agent.id)
            }
            for agent in agents
        ],
        "total": len(agents)
    }


@router.get("/{agent_id}")
async def get_subagent(agent_id: str):
    """Obtiene detalles de un subagente específico"""
    if not subagent_registry.is_initialized():
        register_all_subagents()
    
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Subagente no encontrado: {agent_id}"
        )
    
    # Obtener herramientas del agente
    tools = agent.get_tools()
    
    return {
        "subagent": {
            "id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "version": agent.version,
            "domain_tools": agent.domain_tools,
            "system_prompt": agent.system_prompt[:500] + "..." if len(agent.system_prompt) > 500 else agent.system_prompt,
            "status": "active",
            "icon": _get_agent_icon(agent.id),
            "tools": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters
                }
                for t in tools
            ]
        }
    }


@router.get("/{agent_id}/tools")
async def get_subagent_tools(agent_id: str):
    """Obtiene las herramientas de un subagente"""
    if not subagent_registry.is_initialized():
        register_all_subagents()
    
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Subagente no encontrado: {agent_id}"
        )
    
    tools = agent.get_tools()
    
    return {
        "agent_id": agent_id,
        "tools": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "type": t.type.value if hasattr(t.type, 'value') else str(t.type),
                "parameters": t.parameters
            }
            for t in tools
        ],
        "total": len(tools)
    }


# ============================================
# Ejecutar y Probar Subagentes
# ============================================

@router.post("/{agent_id}/execute")
async def execute_subagent(agent_id: str, request: SubagentExecuteRequest):
    """
    Ejecuta una tarea en un subagente específico.
    
    Útil para probar subagentes directamente sin pasar por el Adaptive Agent.
    """
    if not subagent_registry.is_initialized():
        register_all_subagents()
    
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Subagente no encontrado: {agent_id}"
        )
    
    logger.info(
        f"🎯 Direct execution of subagent",
        agent_id=agent_id,
        task=request.task[:100]
    )
    
    try:
        result = await agent.execute(
            task=request.task,
            context=request.context,
            llm_url=request.llm_url,
            model=request.model,
            provider_type=request.provider_type,
            api_key=request.api_key
        )
        
        return {
            "status": "completed",
            "agent_id": agent_id,
            "result": result.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Error executing subagent {agent_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error ejecutando subagente: {str(e)}"
        )


@router.post("/{agent_id}/test")
async def test_subagent(agent_id: str):
    """
    Prueba rápida de un subagente.
    
    Verifica que el subagente está correctamente configurado y sus tools funcionan.
    """
    if not subagent_registry.is_initialized():
        register_all_subagents()
    
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Subagente no encontrado: {agent_id}"
        )
    
    # Verificar tools
    tools = agent.get_tools()
    tools_status = []
    
    for tool in tools:
        tools_status.append({
            "id": tool.id,
            "name": tool.name,
            "has_handler": tool.handler is not None,
            "status": "ok" if tool.handler else "missing_handler"
        })
    
    all_ok = all(t["status"] == "ok" for t in tools_status)
    
    return {
        "agent_id": agent_id,
        "status": "healthy" if all_ok else "degraded",
        "tools_count": len(tools),
        "tools_status": tools_status,
        "checks": {
            "registered": True,
            "has_tools": len(tools) > 0,
            "all_handlers_present": all_ok
        }
    }


# ============================================
# Configuración de Subagentes
# ============================================

@router.get("/{agent_id}/config")
async def get_subagent_config(agent_id: str):
    """Obtiene la configuración actual de un subagente"""
    if not subagent_registry.is_initialized():
        register_all_subagents()
    
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Subagente no encontrado: {agent_id}"
        )
    
    # TODO: Cargar configuración desde Strapi
    config = _get_agent_config(agent_id)
    
    # Añadir system_prompt del agente
    config["system_prompt"] = agent.system_prompt
    
    return {
        "agent_id": agent_id,
        "config": config
    }


@router.put("/{agent_id}/config")
async def update_subagent_config(agent_id: str, config: SubagentConfigUpdate):
    """Actualiza la configuración de un subagente"""
    if not subagent_registry.is_initialized():
        register_all_subagents()
    
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Subagente no encontrado: {agent_id}"
        )
    
    # Actualizar system_prompt si se proporciona
    if config.system_prompt is not None:
        agent.system_prompt = config.system_prompt
        logger.info(
            f"📝 Updated system_prompt for {agent_id}",
            prompt_length=len(config.system_prompt)
        )
    
    # TODO: Guardar configuración completa en Strapi
    logger.info(
        f"📝 Updating subagent config",
        agent_id=agent_id,
        enabled=config.enabled
    )
    
    return {
        "status": "ok",
        "message": f"Configuración de {agent_id} actualizada",
        "agent_id": agent_id,
        "updated": {
            "system_prompt": config.system_prompt is not None,
            "enabled": config.enabled
        }
    }


# ============================================
# Helpers
# ============================================

def _get_agent_icon(agent_id: str) -> str:
    """Retorna el icono para un subagente"""
    icons = {
        "media_agent": "image",
        "slides_agent": "slideshow",
        "sap_agent": "business",
        "mail_agent": "email",
        "office_agent": "description"
    }
    return icons.get(agent_id, "smart_toy")


def _get_agent_config(agent_id: str) -> Dict[str, Any]:
    """Obtiene configuración de un subagente (placeholder para Strapi)"""
    # TODO: Implementar lectura desde Strapi
    default_configs = {
        "media_agent": {
            "enabled": True,
            "default_provider": "openai",
            "default_model": "dall-e-3",
            "default_size": "1024x1024",
            "max_concurrent": 3,
            "settings": {
                "quality": "standard",
                "style": "vivid"
            }
        }
    }
    
    return default_configs.get(agent_id, {
        "enabled": True,
        "settings": {}
    })
