"""
OpenAI Native Web Search Agent
Agente que usa el web search nativo de OpenAI (solo para gpt-4o-mini, gpt-4o, gpt-4-turbo)
"""

from typing import AsyncGenerator, Optional
import structlog

from ..models import (
    ChainDefinition,
    ChainConfig,
    NodeDefinition,
    NodeType,
    StreamEvent
)
from ..registry import chain_registry
from .native_web_search import (
    call_llm_with_web_search,
    call_llm_with_web_search_stream,
    is_web_search_supported,
    get_web_search_info
)

logger = structlog.get_logger()


# System prompt optimizado para web search
OPENAI_WEB_SEARCH_SYSTEM_PROMPT = """Eres un asistente inteligente con acceso a búsqueda web en tiempo real.

CAPACIDADES:
- Tienes acceso directo a búsqueda web usando Bing
- Puedes buscar información actualizada automáticamente
- Debes usar búsqueda web cuando:
  * Se te pregunta sobre noticias recientes
  * Necesitas datos actualizados (precios, clima, etc.)
  * El usuario pregunta "busca..." o "encuentra..."
  * La información puede haber cambiado recientemente

INSTRUCCIONES:
1. Analiza la pregunta del usuario
2. Si necesitas información actualizada, úsala automáticamente
3. Cita las fuentes cuando uses información de búsqueda
4. Si no encuentras información relevante, indícalo claramente
5. Responde en español de forma clara y concisa

IMPORTANTE:
- No inventes información
- Si no estás seguro, admítelo
- Prioriza fuentes confiables
- Fecha actual para contexto: {current_date}
"""


async def build_openai_web_search_agent(
    config: ChainConfig,
    llm_url: str,
    model: str,
    input_data: dict,
    memory: list,
    execution_id: str = "",
    stream: bool = True,
    provider_type: str = "openai",
    api_key: Optional[str] = None,
    **kwargs
):
    """
    Builder del agente con web search nativo de OpenAI.
    
    Requiere:
    - provider_type = "openai"
    - api_key de OpenAI
    - model que soporte web search (gpt-4o-mini, gpt-4o, gpt-4-turbo)
    """
    
    query = input_data.get("message", input_data.get("query", ""))
    
    # Validaciones
    if provider_type.lower() != "openai":
        error_msg = f"Este agente requiere OpenAI, recibido: {provider_type}"
        logger.error(error_msg)
        yield StreamEvent(
            event_type="error",
            execution_id=execution_id,
            node_id="validation",
            content=error_msg
        )
        return
    
    if not api_key:
        error_msg = "API key de OpenAI requerida para web search nativo"
        logger.error(error_msg)
        yield StreamEvent(
            event_type="error",
            execution_id=execution_id,
            node_id="validation",
            content=error_msg
        )
        return
    
    if not is_web_search_supported(model):
        warning_msg = f"⚠️ Modelo {model} puede no soportar web search. Recomendados: gpt-4o-mini, gpt-4o, gpt-4-turbo"
        logger.warning(warning_msg)
        yield StreamEvent(
            event_type="warning",
            execution_id=execution_id,
            node_id="validation",
            content=warning_msg
        )
    
    # Inicio
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="web_search",
        node_name="🌐 OpenAI Web Search",
        data={
            "model": model,
            "query": query,
            "web_search_enabled": True
        }
    )
    
    # Preparar mensajes
    from datetime import datetime
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    system_prompt = OPENAI_WEB_SEARCH_SYSTEM_PROMPT.format(current_date=current_date)
    
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Agregar memoria (últimos N mensajes)
    if memory:
        messages.extend(memory[-config.max_memory_messages:] if config.use_memory else [])
    
    # Agregar query actual
    messages.append({"role": "user", "content": query})
    
    logger.info(
        "Ejecutando OpenAI Web Search Agent",
        model=model,
        query_length=len(query),
        with_memory=len(memory) > 0
    )
    
    if stream:
        # Modo streaming
        full_response = ""
        web_searches_performed = []
        
        async for event in call_llm_with_web_search_stream(
            model=model,
            messages=messages,
            api_key=api_key,
            temperature=config.temperature,
            base_url=llm_url if "openai.com" not in llm_url else "https://api.openai.com/v1"
        ):
            event_type = event.get("type")
            content = event.get("content", "")
            metadata = event.get("metadata", {})
            
            if event_type == "token":
                full_response += content
                yield StreamEvent(
                    event_type="token",
                    execution_id=execution_id,
                    node_id="web_search",
                    content=content
                )
            
            elif event_type == "web_search":
                web_searches_performed.append(metadata)
                yield StreamEvent(
                    event_type="tool_call",
                    execution_id=execution_id,
                    node_id="web_search",
                    node_name="🔍 Búsqueda Web",
                    data=metadata
                )
            
            elif event_type == "done":
                yield StreamEvent(
                    event_type="node_end",
                    execution_id=execution_id,
                    node_id="web_search",
                    node_name="🌐 OpenAI Web Search",
                    data={
                        "response": full_response[:500],
                        "web_searches_count": len(web_searches_performed),
                        "web_searches": web_searches_performed,
                        "model": model
                    }
                )
            
            elif event_type == "error":
                yield StreamEvent(
                    event_type="error",
                    execution_id=execution_id,
                    node_id="web_search",
                    content=content
                )
    
    else:
        # Modo no-streaming
        result = await call_llm_with_web_search(
            model=model,
            messages=messages,
            api_key=api_key,
            temperature=config.temperature,
            base_url=llm_url if "openai.com" not in llm_url else "https://api.openai.com/v1",
            stream=False
        )
        
        if result.get("success"):
            content = result.get("content", "")
            web_searches = result.get("web_searches", [])
            
            yield StreamEvent(
                event_type="node_end",
                execution_id=execution_id,
                node_id="web_search",
                node_name="🌐 OpenAI Web Search",
                data={
                    "response": content,
                    "web_searches_count": len(web_searches),
                    "web_searches": web_searches,
                    "usage": result.get("usage", {})
                }
            )
            
            # Resultado para modo no-streaming
            yield {"_result": {
                "response": content,
                "web_searches": web_searches,
                "model": model,
                "usage": result.get("usage", {})
            }}
        else:
            error_msg = result.get("error", "Error desconocido")
            yield StreamEvent(
                event_type="error",
                execution_id=execution_id,
                node_id="web_search",
                content=error_msg
            )


def register_openai_web_search_agent():
    """Registrar el agente de web search nativo de OpenAI"""
    
    definition = ChainDefinition(
        id="openai_web_search",
        name="OpenAI Native Web Search",
        description="Agente que usa el web search nativo de OpenAI (Bing). Solo funciona con gpt-4o-mini, gpt-4o, gpt-4-turbo. Requiere API key de OpenAI.",
        type="agent",
        version="1.0.0",
        nodes=[
            NodeDefinition(id="input", type=NodeType.INPUT, name="Query"),
            NodeDefinition(
                id="web_search",
                type=NodeType.LLM,
                name="Web Search Nativo",
                system_prompt=OPENAI_WEB_SEARCH_SYSTEM_PROMPT
            ),
            NodeDefinition(id="output", type=NodeType.OUTPUT, name="Respuesta")
        ],
        config=ChainConfig(
            temperature=0.7,
            use_memory=True,
            max_memory_messages=10
        )
    )
    
    chain_registry.register(
        chain_id="openai_web_search",
        definition=definition,
        builder=build_openai_web_search_agent
    )
    
    logger.info("OpenAI Web Search Agent registrado")
