"""
Agent Delegation Tool - Permite al Unified Agent delegar a agentes especializados
"""

import json
from typing import Dict, Any, Optional
import structlog

from ..engine.registry import chain_registry
from ..engine.models import ChainConfig

logger = structlog.get_logger()


async def delegate_to_agent(
    agent_id: str,
    task: str,
    context: Optional[str] = None,
    # Contexto LLM heredado del Unified Agent
    _llm_url: Optional[str] = None,
    _model: Optional[str] = None,
    _provider_type: Optional[str] = None,
    _api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Herramienta que permite al Unified Agent delegar tareas a agentes especializados.
    
    Args:
        agent_id: ID del agente especializado (sap_agent, rag, tool_agent, etc.)
        task: Descripción clara de la tarea a realizar
        context: Contexto adicional o resultados de pasos previos (opcional)
        _llm_url: URL del LLM (heredada del Unified Agent)
        _model: Modelo LLM (heredado del Unified Agent)
        _provider_type: Provider type (heredado del Unified Agent)
        _api_key: API key (heredada del Unified Agent)
    
    Returns:
        Dict con resultado del agente: {success, response, agent_name, tools_used, sources, images}
    
    Ejemplo:
        result = await delegate_to_agent(
            agent_id="sap_agent",
            task="Obtener lista de pedidos del día de hoy",
            context="Usuario solicita análisis de ventas"
        )
    """
    logger.info(f"🎯 Delegating to agent", agent_id=agent_id, task=task[:100])
    
    # Obtener builder y definición del agente
    builder = chain_registry.get_builder(agent_id)
    definition = chain_registry.get(agent_id)
    
    if not builder or not definition:
        logger.error(f"❌ Agent not found: {agent_id}")
        return {
            "success": False,
            "error": f"Agente '{agent_id}' no encontrado en el registry",
            "available_agents": chain_registry.list_chain_ids(),
            "agent_name": agent_id
        }
    
    try:
        # Preparar mensaje con contexto si está disponible
        message = task
        if context:
            message = f"{task}\n\nCONTEXTO:\n{context}"
        
        # Input para el sub-agente
        sub_input = {
            "message": message,
            "query": message
        }
        
        # Ejecutar agente en modo no-streaming para capturar resultado completo
        result = None
        full_response = ""
        tools_used = []
        sources = []
        images = []
        
        # Usar contexto LLM heredado (crucial para que funcione)
        llm_url = _llm_url
        model = _model
        provider_type = _provider_type
        api_key = _api_key
        
        logger.debug(
            f"Executing sub-agent with inherited context",
            provider=provider_type,
            model=model,
            llm_url=llm_url
        )
        
        # Ejecutar el builder
        async for event in builder(
            config=definition.config,
            llm_url=llm_url,
            model=model,
            input_data=sub_input,
            memory=[],  # Sin memoria (cada delegación es independiente)
            execution_id=f"delegate_{agent_id}",
            stream=False,
            provider_type=provider_type,
            api_key=api_key
        ):
            # Capturar eventos de imagen
            if hasattr(event, 'event_type') and event.event_type == "image":
                if event.data:
                    images.append({
                        "url": event.data.get("image_url"),
                        "base64": event.data.get("image_data"),
                        "mime_type": event.data.get("mime_type", "image/png"),
                        "alt_text": event.data.get("alt_text", "Generated content")
                    })
            
            # Capturar resultado final
            if isinstance(event, dict) and "_result" in event:
                result = event["_result"]
                full_response = result.get("response", "")
                tools_used = result.get("tools_used", [])
                sources = result.get("sources", [])
                break
            
            # Capturar tokens si no hay _result
            if hasattr(event, 'event_type'):
                if event.event_type == "token" and event.content:
                    full_response += event.content
                elif event.event_type == "node_end" and event.data:
                    if "response" in event.data:
                        full_response = event.data["response"]
                    if "tools_used" in event.data:
                        tools_used = event.data.get("tools_used", [])
                    if "sources" in event.data:
                        sources = event.data.get("sources", [])
        
        logger.info(
            f"✅ Agent delegation completed",
            agent_id=agent_id,
            response_length=len(full_response),
            tools_used=len(tools_used),
            images=len(images)
        )
        
        return {
            "success": True,
            "response": full_response,
            "agent_name": definition.name,
            "agent_id": agent_id,
            "tools_used": tools_used,
            "sources": sources,
            "images": images,
            "has_images": len(images) > 0,
            "has_sources": len(sources) > 0
        }
    
    except Exception as e:
        logger.error(f"❌ Error delegating to agent {agent_id}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "agent_name": definition.name if definition else agent_id,
            "agent_id": agent_id
        }


def get_available_agents_description() -> str:
    """
    Genera descripción de todos los agentes disponibles para inyectar en prompts.
    
    Returns:
        String con lista de agentes y sus descripciones
    """
    agents = []
    for chain_id in chain_registry.list_chain_ids():
        # Excluir el unified_agent y orchestrator de la lista
        if chain_id in ["unified_agent", "orchestrator"]:
            continue
        
        definition = chain_registry.get(chain_id)
        if definition:
            agents.append(f"- {chain_id}: {definition.description}")
    
    if not agents:
        return "- conversational: Chat general y respuestas"
    
    return "\n".join(agents)


def get_agents_enum() -> list:
    """
    Obtiene lista de IDs de agentes para schema de herramienta.
    
    Returns:
        Lista de IDs de agentes disponibles (excluyendo unified_agent y orchestrator)
    """
    return [
        chain_id
        for chain_id in chain_registry.list_chain_ids()
        if chain_id not in ["unified_agent", "orchestrator"]
    ]
