"""
OpenAI Native Web Search Agent (REFACTORIZADO con estándar)
Agente que usa el web search nativo de OpenAI (solo para gpt-4o-mini, gpt-4o, gpt-4-turbo)
Usa automáticamente la API key configurada en Strapi.
"""

from typing import AsyncGenerator, Optional
from datetime import datetime
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
    is_web_search_supported
)
from ...providers.llm_provider import get_provider_by_type
from .agent_helpers import build_llm_messages  # ✅ Usar helper compartido

logger = structlog.get_logger()


# ============================================
# Definición del Agente (con prompts editables)
# ============================================

OPENAI_WEB_SEARCH_DEFINITION = ChainDefinition(
    id="openai_web_search",
    name="OpenAI Native Web Search",
    description="Agente que usa el web search nativo de OpenAI (Bing). Funciona con gpt-4o-mini, gpt-4o, gpt-4-turbo. Usa automáticamente la API key del provider OpenAI configurado en Strapi.",
    type="agent",
    version="2.0.0",  # ✅ Versión actualizada
    nodes=[
        NodeDefinition(
            id="input",
            type=NodeType.INPUT,
            name="Query"
        ),
        NodeDefinition(
            id="web_search",
            type=NodeType.LLM,
            name="Web Search Nativo",
            # ✅ System prompt editable con variable
            system_prompt="""Eres un asistente inteligente con acceso a búsqueda web en tiempo real.

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
- Fecha actual para contexto: {{current_date}}""",
            # ✅ Template con variable
            prompt_template="{{user_query}}",
            temperature=0.7
        ),
        NodeDefinition(
            id="output",
            type=NodeType.OUTPUT,
            name="Respuesta"
        )
    ],
    config=ChainConfig(
        temperature=0.7,
        use_memory=True,
        max_memory_messages=10
    )
)


# ============================================
# Builder Function (Lógica del Agente)
# ============================================

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
) -> AsyncGenerator[StreamEvent, None]:
    """
    Builder del agente con web search nativo de OpenAI.
    
    FASES:
    1. Configuration: Obtener provider OpenAI desde Strapi
    2. Web Search: Búsqueda web con OpenAI Responses API
    
    NODOS:
    - input (INPUT): Query del usuario
    - web_search (LLM): Búsqueda con OpenAI + Bing
    - output (OUTPUT): Respuesta con información actualizada
    
    MEMORY: Yes (últimos 10 mensajes)
    TOOLS: OpenAI Web Search (Bing nativo)
    
    REQUIREMENTS:
    - Provider OpenAI configurado en Strapi
    - Modelo compatible: gpt-4o-mini, gpt-4o, gpt-4-turbo
    """
    
    logger.warning(
        "🔵 INICIO build_openai_web_search_agent",
        model_recibido=model,
        provider_type_recibido=provider_type
    )
    
    query = input_data.get("message", input_data.get("query", ""))
    
    # ✅ Obtener nodo con prompt editable
    web_search_node = OPENAI_WEB_SEARCH_DEFINITION.get_node("web_search")
    if not web_search_node:
        raise ValueError("Nodo web_search no encontrado")
    
    # ========== FASE 1: CONFIGURATION ==========
    # SIEMPRE obtener configuración del provider OpenAI desde Strapi
    logger.warning(
        "Obteniendo configuración del provider OpenAI desde Strapi",
        received_provider_type=provider_type
    )
    
    try:
        provider = await get_provider_by_type("openai")
        
        if provider:
            # Sobrescribir con valores de OpenAI
            api_key = provider.api_key
            llm_url = provider.base_url
            model = provider.default_model
            provider_type = "openai"
            logger.warning(
                f"Provider OpenAI encontrado: {provider.name}",
                model=model,
                base_url=llm_url
            )
        else:
            logger.warning("No se encontró provider OpenAI activo en Strapi")
            provider = None
    except Exception as e:
        logger.error(f"Error obteniendo provider OpenAI: {e}")
        provider = None
    
    # Validación: debe haber provider OpenAI
    if not provider or not api_key:
        error_msg = (
            "No se encontró configuración de OpenAI. "
            "Configura un LLM Provider OpenAI activo en Strapi."
        )
        logger.error(error_msg)
        yield StreamEvent(
            event_type="error",
            execution_id=execution_id,
            node_id="validation",
            content=error_msg
        )
        return
    
    # Validar modelo compatible
    if not is_web_search_supported(model):
        warning_msg = f"⚠️ Modelo {model} puede no soportar web search. Recomendados: gpt-4o-mini, gpt-4o, gpt-4-turbo"
        logger.warning(warning_msg)
        yield StreamEvent(
            event_type="warning",
            execution_id=execution_id,
            node_id="validation",
            content=warning_msg
        )
    
    # ========== FASE 2: WEB SEARCH ==========
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
    
    # ✅ Construir mensajes con helper estándar
    current_date = datetime.now().strftime("%Y-%m-%d")
    system_prompt = web_search_node.system_prompt.replace("{{current_date}}", current_date)
    
    messages = build_llm_messages(
        system_prompt=system_prompt,
        template=web_search_node.prompt_template,
        variables={"user_query": query},
        memory=memory,
        max_memory=config.max_memory_messages if config.use_memory else 0
    )
    
    logger.warning(
        "Ejecutando OpenAI Web Search Agent (Responses API)",
        model=model,
        query_length=len(query),
        with_memory=len(memory) > 0
    )
    
    # Indicador de búsqueda
    yield StreamEvent(
        event_type="token",
        execution_id=execution_id,
        node_id="web_search",
        content="🔍 Buscando en la web..."
    )
    
    # Llamada a OpenAI Responses API con web search
    result = await call_llm_with_web_search(
        model=model,
        messages=messages,
        api_key=api_key,
        temperature=web_search_node.temperature,
        base_url=llm_url if "openai.com" not in llm_url else "https://api.openai.com/v1",
        stream=False
    )
    
    if result.get("success"):
        content = result.get("content", "")
        
        # Simular streaming enviando el contenido
        yield StreamEvent(
            event_type="token",
            execution_id=execution_id,
            node_id="web_search",
            content=content
        )
        
        yield StreamEvent(
            event_type="node_end",
            execution_id=execution_id,
            node_id="web_search",
            node_name="🌐 OpenAI Web Search",
            data={
                "response": content[:500],
                "model": model,
                "status": result.get("status"),
                "response_id": result.get("response_id")
            }
        )
        
        # Resultado para modo no-streaming
        if not stream:
            yield {"_result": {
                "response": content,
                "model": model,
                "status": result.get("status")
            }}
    else:
        error_msg = result.get("error", "Error desconocido")
        yield StreamEvent(
            event_type="error",
            execution_id=execution_id,
            node_id="web_search",
            content=error_msg
        )


# ============================================
# Registro del Agente
# ============================================

def register_openai_web_search_agent():
    """Registrar el agente de web search nativo de OpenAI"""
    
    chain_registry.register(
        chain_id="openai_web_search",
        definition=OPENAI_WEB_SEARCH_DEFINITION,
        builder=build_openai_web_search_agent
    )
    
    logger.info("OpenAI Web Search Agent registrado (v2.0.0)")
