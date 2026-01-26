"""
Unified Agent - Agente neuronal con tool calling nativo
Arquitectura prompt-driven donde el LLM controla el flujo de ejecución
"""

import json
from typing import AsyncGenerator, Optional
from datetime import datetime

from ..models import (
    ChainDefinition,
    ChainConfig,
    NodeDefinition,
    NodeType,
    StreamEvent
)
from ..registry import chain_registry
from .llm_utils import call_llm_with_tools, LLMToolResponse, ToolCall
from .agent_helpers import build_llm_messages
from .prompts import UNIFIED_AGENT_MASTER_PROMPT
from ...tools import tool_registry, get_available_agents_description

import structlog

logger = structlog.get_logger()


# ============================================
# Definición del Agente
# ============================================

UNIFIED_AGENT_DEFINITION = ChainDefinition(
    id="unified_agent",
    name="Unified Intelligent Agent",
    description="Agente inteligente neuronal que coordina otros agentes mediante tool calling nativo. El LLM controla el flujo de ejecución completo.",
    type="unified",
    version="1.0.0",
    nodes=[
        NodeDefinition(
            id="master",
            type=NodeType.LLM,
            name="Master Agent",
            system_prompt=UNIFIED_AGENT_MASTER_PROMPT,
            temperature=0.3  # Más determinístico para coordinación
        )
    ],
    config=ChainConfig(
        use_memory=True,
        max_memory_messages=20,
        temperature=0.3
    )
)


# ============================================
# Builder Function
# ============================================

async def build_unified_agent(
    config: ChainConfig,
    llm_url: str,
    model: str,
    input_data: dict,
    memory: list,
    execution_id: str = "",
    stream: bool = True,
    provider_type: str = "ollama",
    api_key: Optional[str] = None,
    **kwargs
) -> AsyncGenerator[StreamEvent, None]:
    """
    Agente unificado con tool calling nativo.
    
    El LLM decide qué herramientas usar y cuándo, sin loop hardcoded.
    
    FLOW:
    1. Inyectar contexto (agentes, herramientas)
    2. Loop de tool calling (max 20 iteraciones):
       - LLM decide qué tool usar
       - Ejecutar tool
       - Si tool=finish: terminar
       - Sino: añadir resultado y continuar
    3. Streaming de eventos
    
    Args:
        config: Configuración de la cadena
        llm_url: URL del LLM
        model: Nombre del modelo
        input_data: Datos de entrada {"message": "..."}
        memory: Historial de conversación
        execution_id: ID de ejecución
        stream: Si hacer streaming o no
        provider_type: Tipo de provider (ollama, openai, anthropic, etc.)
        api_key: API key si es necesario
    
    Yields:
        StreamEvent con progreso de ejecución
    """
    query = input_data.get("message", input_data.get("query", ""))
    max_iterations = input_data.get("max_iterations", 20)
    
    logger.info(
        "🚀 Starting Unified Agent",
        query=query[:100],
        model=model,
        provider=provider_type,
        max_iterations=max_iterations
    )
    
    # Obtener descripción de agentes disponibles
    agents_description = get_available_agents_description()
    
    # Preparar system prompt con context injection
    system_prompt = UNIFIED_AGENT_MASTER_PROMPT.format(
        agents_description=agents_description,
        user_query=query
    )
    
    # Construir mensajes iniciales con memoria
    messages = build_llm_messages(
        system_prompt=system_prompt,
        template="",  # Query ya está en system prompt
        variables={},
        memory=memory,
        max_memory=config.max_memory_messages
    )
    
    # Obtener tools disponibles en formato para el LLM
    tools = tool_registry.get_tools_for_llm()
    
    logger.debug(
        f"Tools available: {len(tools)}",
        tools=[t['name'] for t in tools]
    )
    
    # Yield evento de inicio
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="master",
        node_name="🧠 Unified Agent",
        data={
            "query": query,
            "model": model,
            "provider": provider_type,
            "tools_available": len(tools),
            "agents_available": agents_description.count("-")
        }
    )
    
    # ============================================
    # Loop de Tool Calling
    # ============================================
    
    iteration = 0
    finished = False
    final_answer = None
    
    while iteration < max_iterations and not finished:
        iteration += 1
        
        logger.info(f"🔄 Iteration {iteration}/{max_iterations}")
        
        try:
            # Llamar al LLM con tools
            response: LLMToolResponse = await call_llm_with_tools(
                llm_url=llm_url,
                model=model,
                messages=messages,
                tools=tools,
                temperature=config.temperature,
                provider_type=provider_type,
                api_key=api_key
            )
            
            # Si el LLM respondió directamente sin usar tools
            if response.content and not response.tool_calls:
                logger.warning(
                    "⚠️  LLM respondió sin usar finish(). Forzando finish.",
                    content_preview=response.content[:100]
                )
                # Forzar finish con el contenido
                final_answer = response.content
                finished = True
                
                yield StreamEvent(
                    event_type="token",
                    execution_id=execution_id,
                    node_id="master",
                    content=response.content
                )
                break
            
            # Procesar tool calls
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call.function.get("name")
                    tool_args_str = tool_call.function.get("arguments", "{}")
                    
                    # Parsear argumentos
                    try:
                        tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Error parsing tool arguments: {e}", args=tool_args_str)
                        tool_args = {}
                    
                    logger.info(
                        f"🔧 Tool call: {tool_name}",
                        args=str(tool_args)[:200]
                    )
                    
                    # Yield evento de tool call
                    yield StreamEvent(
                        event_type="tool_call",
                        execution_id=execution_id,
                        node_id="master",
                        node_name=f"Tool: {tool_name}",
                        data={
                            "tool": tool_name,
                            "arguments": tool_args
                        }
                    )
                    
                    # Ejecutar tool
                    try:
                        # Inyectar contexto LLM para la tool delegate
                        if tool_name == "delegate":
                            tool_args["_llm_url"] = llm_url
                            tool_args["_model"] = model
                            tool_args["_provider_type"] = provider_type
                            tool_args["_api_key"] = api_key
                        
                        result = await tool_registry.execute(tool_name, **tool_args)
                        
                        logger.info(
                            f"✅ Tool completed: {tool_name}",
                            success=result.get("success", True)
                        )
                        
                        # Yield evento de resultado
                        yield StreamEvent(
                            event_type="tool_result",
                            execution_id=execution_id,
                            node_id="master",
                            data={
                                "tool": tool_name,
                                "result_preview": str(result)[:500]
                            }
                        )
                        
                        # Si es finish(), terminar ejecución
                        if tool_name == "finish":
                            final_answer = result.get("final_answer", result.get("answer", ""))
                            finished = True
                            
                            # Stream la respuesta final
                            if final_answer:
                                yield StreamEvent(
                                    event_type="token",
                                    execution_id=execution_id,
                                    node_id="master",
                                    content=final_answer
                                )
                            
                            logger.info("🏁 Agent finished via finish() tool")
                            break
                        
                        # Añadir resultado a mensajes para el siguiente turno
                        # Formato depende del provider:
                        # - Ollama: {"role": "tool", "tool_name": "...", "content": "..."}
                        # - OpenAI/Anthropic: {"role": "tool", "tool_call_id": "...", "name": "...", "content": "..."}
                        
                        # Mensaje assistant con tool_calls (común para todos)
                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "arguments": tool_args_str
                                }
                            }]
                        })
                        
                        # Mensaje tool con formato específico del provider
                        if provider_type == "ollama":
                            # Formato Ollama
                            messages.append({
                                "role": "tool",
                                "tool_name": tool_name,
                                "content": json.dumps(result, ensure_ascii=False)
                            })
                        else:
                            # Formato OpenAI/Anthropic/Groq/Gemini
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool_name,
                                "content": json.dumps(result, ensure_ascii=False)
                            })
                        
                    except Exception as e:
                        logger.error(f"❌ Error executing tool {tool_name}: {e}", exc_info=True)
                        
                        # Informar del error al LLM
                        error_msg = {
                            "error": str(e),
                            "tool": tool_name,
                            "message": f"La herramienta {tool_name} falló. Intenta otra estrategia o usa finish() para informar al usuario."
                        }
                        
                        # Informar del error al LLM con formato específico del provider
                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "arguments": tool_args_str
                                }
                            }]
                        })
                        
                        if provider_type == "ollama":
                            messages.append({
                                "role": "tool",
                                "tool_name": tool_name,
                                "content": json.dumps(error_msg, ensure_ascii=False)
                            })
                        else:
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool_name,
                                "content": json.dumps(error_msg, ensure_ascii=False)
                            })
                        
                        yield StreamEvent(
                            event_type="error",
                            execution_id=execution_id,
                            node_id="master",
                            content=f"Error en {tool_name}: {str(e)}"
                        )
            else:
                # No tool calls y no content - esto no debería pasar
                logger.warning("⚠️  LLM no generó tool calls ni content")
                break
                
        except Exception as e:
            logger.error(f"❌ Error en iteración {iteration}: {e}", exc_info=True)
            yield StreamEvent(
                event_type="error",
                execution_id=execution_id,
                node_id="master",
                content=f"Error del sistema: {str(e)}"
            )
            break
    
    # ============================================
    # Finalización
    # ============================================
    
    if not finished:
        if iteration >= max_iterations:
            logger.warning(f"⚠️  Max iterations reached ({max_iterations})")
            yield StreamEvent(
                event_type="error",
                execution_id=execution_id,
                node_id="master",
                content="Se alcanzó el límite máximo de iteraciones. Por favor reformula tu pregunta."
            )
        else:
            logger.warning("⚠️  Agent terminated without finish()")
            yield StreamEvent(
                event_type="error",
                execution_id=execution_id,
                node_id="master",
                content="El agente terminó inesperadamente sin proporcionar respuesta."
            )
    
    # Yield evento de fin
    yield StreamEvent(
        event_type="node_end",
        execution_id=execution_id,
        node_id="master",
        node_name="🧠 Unified Agent",
        data={
            "iterations": iteration,
            "finished": finished,
            "answer_length": len(final_answer) if final_answer else 0
        }
    )
    
    logger.info(
        "✅ Unified Agent completed",
        iterations=iteration,
        finished=finished
    )


# ============================================
# Registro del Agente
# ============================================

def register_unified_agent():
    """Registrar el agente unificado en el registry"""
    
    chain_registry.register(
        chain_id="unified_agent",
        definition=UNIFIED_AGENT_DEFINITION,
        builder=build_unified_agent
    )
    
    logger.info("✅ Unified Agent registrado (v1.0.0)")
