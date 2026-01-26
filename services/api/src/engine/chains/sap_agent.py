"""
SAP Agent - Agente con herramientas SAP OpenAPI usando TOOL CALLING NATIVO
Refactorizado para usar el mismo patrón que Unified Agent (robusto y consistente)
Version 3.0.0 - Tool Calling Native
"""

import json
from typing import AsyncGenerator, Optional, List, Dict, Any
from datetime import datetime

from ..models import (
    ChainDefinition,
    ChainConfig,
    NodeDefinition,
    NodeType,
    StreamEvent
)
from ..registry import chain_registry
from ...tools import tool_registry
from .llm_utils import call_llm_with_tools, LLMToolResponse, ToolCall
from .agent_helpers import build_llm_messages

import structlog

logger = structlog.get_logger()


# ============================================
# Funciones de herramientas SAP
# ============================================

async def get_sap_tools() -> list:
    """
    Obtener herramientas SAP en formato para tool calling nativo.
    Retorna lista de tools en formato OpenAI para el LLM.
    """
    # Asegurar que las tools OpenAPI están cargadas
    await tool_registry.load_openapi_tools()
    
    # Filtrar solo herramientas SAP
    sap_tools = [t for t in tool_registry.tools.values() 
                 if t.id.startswith("sap_btp_gateway")]
    
    logger.info(f"📋 get_sap_tools() found {len(sap_tools)} SAP tools")
    
    # Incluir TODAS las tools (OpenAI puede manejar hasta 128)
    # Priorizamos completitud sobre contexto
    return [tool.to_function_schema() for tool in sap_tools]


async def execute_sap_tool(tool_id: str, parameters: dict) -> dict:
    """Ejecutar una herramienta SAP via tool_registry"""
    return await tool_registry.execute(tool_id, **parameters)


# ============================================
# Helper Functions - Message Formatting
# ============================================

def format_tool_result_for_ollama(result: Dict[str, Any]) -> str:
    """
    Formatea el resultado de una tool para Ollama.
    Ollama funciona mejor con texto plano simple en lugar de JSON complejo.
    """
    if not result.get("success"):
        return f"Error: {result.get('error', 'Unknown error')}"
    
    data = result.get("data", {})
    
    # Caso especial: lista de usuarios
    if isinstance(data, dict) and "users" in data:
        users_list = data["users"]
        content_text = f"Success: {len(users_list)} users found\n"
        content_text += "\n".join([
            f"- {u.get('username')}: {u.get('fullname', 'N/A')}" 
            for u in users_list[:20]
        ])
        if len(users_list) > 20:
            content_text += f"\n... and {len(users_list) - 20} more users"
        return content_text
    
    # Caso especial: lista genérica
    if isinstance(data, list):
        content_text = f"Success: {len(data)} items returned\n"
        content_text += str(data[:5])
        if len(data) > 5:
            content_text += f"\n... and {len(data) - 5} more items"
        return content_text
    
    # Caso genérico: convertir a string y truncar
    return f"Success: {str(data)[:500]}"


def format_tool_result_for_openai(result: Dict[str, Any]) -> str:
    """
    Formatea el resultado de una tool para OpenAI/Anthropic.
    Estos providers pueden manejar JSON completo pero necesitamos truncar si es muy grande.
    """
    try:
        result_str = json.dumps(result, ensure_ascii=False)
        
        # Si es muy grande, truncar con resumen
        if len(result_str) > 8000:
            logger.warning(f"Result too large ({len(result_str)} chars), truncating")
            result_summary = {
                "success": result.get("success"),
                "status_code": result.get("status_code"),
                "data_preview": str(result.get("data", {}))[:2000],
                "message": f"Result truncated. Original size: {len(result_str)} chars"
            }
            result_str = json.dumps(result_summary, ensure_ascii=False)
        
        return result_str
    
    except (TypeError, ValueError) as e:
        logger.error(f"JSON serialization error: {e}")
        return json.dumps({
            "error": "Could not serialize result",
            "message": str(result)[:500]
        })


def add_assistant_message_with_tool_calls(
    messages: List[Dict],
    tool_calls: List[ToolCall],
    provider_type: str
) -> None:
    """
    Agrega el mensaje assistant con tool_calls al array de mensajes.
    Solo para OpenAI/Anthropic (Ollama no lo necesita ya que viene en la respuesta).
    
    IMPORTANTE: Esta función MODIFICA la lista messages in-place.
    """
    if provider_type == "ollama":
        # Ollama no necesita este mensaje porque ya está incluido en la respuesta del LLM
        return
    
    # OpenAI/Anthropic/Groq/Gemini necesitan el mensaje assistant antes de los tool results
    messages.append({
        "role": "assistant",
        "content": None,
        "tool_calls": [{
            "id": tc.id,
            "type": "function",
            "function": {
                "name": tc.function.get("name"),
                "arguments": tc.function.get("arguments", "{}")
            }
        } for tc in tool_calls]
    })


def add_tool_result_message(
    messages: List[Dict],
    tool_call: ToolCall,
    result: Dict[str, Any],
    provider_type: str
) -> None:
    """
    Agrega el mensaje con el resultado de la tool al array de mensajes.
    Formato específico según el provider.
    
    IMPORTANTE: Esta función MODIFICA la lista messages in-place.
    """
    if provider_type == "ollama":
        # Ollama: texto plano simple
        content = format_tool_result_for_ollama(result)
        messages.append({
            "role": "tool",
            "content": content
        })
    else:
        # OpenAI/Anthropic/Groq/Gemini: JSON + tool_call_id + name
        content = format_tool_result_for_openai(result)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_call.function.get("name"),
            "content": content
        })


# ============================================
# Definición del Agente (Tool Calling Nativo)
# ============================================

SAP_AGENT_SYSTEM_PROMPT = """You are an SAP assistant with DIRECT ACCESS to SAP tools.

# CRITICAL RULES

1. **YOU MUST USE TOOLS** - You have SAP tools available. USE THEM immediately when users ask for SAP data.
2. **DO NOT ask for clarification** - If the user wants SAP data, call the appropriate tool NOW.
3. **ALWAYS call tools on the FIRST turn** - Don't wait or ask questions.

# AVAILABLE TOOLS

You have access to SAP endpoints for:
- Users (sap_btp_gateway_get_api_users)
- Sales orders (sap_btp_gateway_get_api_sales-orders)
- Products (sap_btp_gateway_get_api_products)
- Bank balances (sap_btp_gateway_get_api_bank-balances)
- And more...

# WORKFLOW

User asks for SAP data → **IMMEDIATELY call the appropriate tool** → Present results

# EXAMPLES

**User**: "Get SAP users list"
→ **ACTION**: Call sap_btp_gateway_get_api_users NOW

**User**: "Show me sales orders"
→ **ACTION**: Call sap_btp_gateway_get_api_sales-orders NOW

**User**: "List products"
→ **ACTION**: Call sap_btp_gateway_get_api_products NOW

# YOUR TASK

User query: {user_query}

**CALL THE APPROPRIATE SAP TOOL NOW. DO NOT RESPOND WITHOUT CALLING A TOOL FIRST.**"""

SAP_AGENT_DEFINITION = ChainDefinition(
    id="sap_agent",
    name="SAP Agent",
    description="Agente inteligente para consultar datos de SAP usando tool calling nativo",
    type="tools",
    version="3.0.0",  # ✅ Nueva versión con tool calling nativo
    nodes=[
        NodeDefinition(
            id="sap_agent",
            type=NodeType.LLM,
            name="SAP Agent",
            system_prompt=SAP_AGENT_SYSTEM_PROMPT,
            temperature=0.3
        )
    ],
    config=ChainConfig(
        temperature=0.3,
        use_memory=True,
        max_memory_messages=6
    )
)


# ============================================
# Builder Function (Tool Calling Nativo)
# ============================================

async def build_sap_agent(
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
    Builder del SAP Agent con TOOL CALLING NATIVO.
    
    NUEVO FLUJO (v3.0):
    1. Cargar herramientas SAP disponibles
    2. LLM decide qué herramienta(s) usar mediante tool calling nativo
    3. Ejecutar herramientas seleccionadas
    4. LLM sintetiza respuesta final con los datos obtenidos
    
    Mucho más robusto que prompt engineering para JSON.
    
    Args:
        config: Configuración de la cadena
        llm_url: URL del LLM
        model: Nombre del modelo
        input_data: {"message": "consulta del usuario"}
        memory: Historial de conversación
        execution_id: ID de ejecución
        stream: Si hacer streaming
        provider_type: Tipo de provider (ollama, openai, anthropic, etc.)
        api_key: API key si es necesario
    
    Yields:
        StreamEvent con progreso de ejecución
    """
    
    query = input_data.get("message", input_data.get("query", ""))
    max_iterations = 2  # Máximo 2 iteraciones (1 inicial + 1 adicional si es necesario)
    
    logger.info(
        "🔵 Starting SAP Agent (Tool Calling Native)",
        query=query[:100],
        model=model,
        provider=provider_type
    )
    
    # ========== FASE 1: CARGAR HERRAMIENTAS SAP ==========
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="sap_loading",
        node_name="🔍 Cargando herramientas SAP",
        data={"query": query, "loading_tools": True}
    )
    
    # Mensaje visible: Cargando herramientas
    yield StreamEvent(
        event_type="token",
        execution_id=execution_id,
        node_id="sap_loading",
        content="Analizando consulta y cargando herramientas SAP disponibles..."
    )
    
    # Cargar herramientas SAP para tool calling
    sap_tools = await get_sap_tools()
    
    logger.info(f"📋 SAP tools loaded: {len(sap_tools)}")
    
    # Mensaje visible: Herramientas cargadas
    yield StreamEvent(
        event_type="token",
        execution_id=execution_id,
        node_id="sap_loading",
        content=f"\n\n✅ {len(sap_tools)} endpoints SAP disponibles"
    )
    
    # Finalizar paso de carga
    yield StreamEvent(
        event_type="node_end",
        execution_id=execution_id,
        node_id="sap_loading",
        data={"tools_loaded": len(sap_tools)}
    )
    if sap_tools:
        logger.debug(f"First 3 SAP tools: {[t.get('function', {}).get('name', t.get('name')) for t in sap_tools[:3]]}")
    
    if not sap_tools:
        error_msg = "No se encontraron herramientas SAP. Verifica que Strapi esté configurado correctamente."
        logger.error(error_msg)
        yield StreamEvent(
            event_type="error",
            execution_id=execution_id,
            node_id="sap_agent",
            content=error_msg
        )
        yield StreamEvent(
            event_type="node_end",
            execution_id=execution_id,
            node_id="sap_agent",
            data={"error": error_msg}
        )
        return
    
    # Preparar system prompt con la query del usuario
    system_prompt = SAP_AGENT_SYSTEM_PROMPT.format(user_query=query)
    
    # Construir mensajes con memoria
    messages = build_llm_messages(
        system_prompt=system_prompt,
        template="",  # La query ya está en el system prompt
        variables={},
        memory=memory,
        max_memory=config.max_memory_messages
    )
    
    # ========== LOOP DE TOOL CALLING ==========
    tool_results = []
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        logger.info(
            f"🔄 SAP Agent iteration {iteration}/{max_iterations}",
            provider=provider_type,
            num_messages=len(messages),
            num_tools=len(sap_tools)
        )
        
        # Iniciar paso de análisis con IA
        analysis_node_id = f"ai_analysis_{iteration}"
        yield StreamEvent(
            event_type="node_start",
            execution_id=execution_id,
            node_id=analysis_node_id,
            node_name=f"🤔 Análisis con IA (iteración {iteration}/{max_iterations})",
            data={"iteration": iteration, "provider": provider_type}
        )
        
        # Mensaje visible: Iteración iniciada
        yield StreamEvent(
            event_type="token",
            execution_id=execution_id,
            node_id=analysis_node_id,
            content=f"Analizando consulta y seleccionando herramientas apropiadas..."
        )
        
        try:
            # ========== LLAMAR AL LLM CON TOOLS ==========
            logger.debug(f"Calling {provider_type} LLM: {llm_url} model={model}")
            
            response: LLMToolResponse = await call_llm_with_tools(
                llm_url=llm_url,
                model=model,
                messages=messages,
                tools=sap_tools,  # Siempre enviar tools
                temperature=config.temperature if iteration == 1 else 0.7,
                provider_type=provider_type,
                api_key=api_key
            )
            
            logger.info(
                f"✅ LLM response received",
                has_content=bool(response.content),
                num_tool_calls=len(response.tool_calls) if response.tool_calls else 0,
                iteration=iteration
            )
            
            # ========== CASO 1: RESPUESTA FINAL (sin tool calls) ==========
            if response.content and not response.tool_calls:
                logger.info(f"📝 LLM provided final answer (iteration {iteration})")
                
                # Finalizar paso de análisis (si aún está activo)
                yield StreamEvent(
                    event_type="node_end",
                    execution_id=execution_id,
                    node_id=analysis_node_id,
                    data={"final_response": True}
                )
                
                # La respuesta final va sin node_id para que se muestre en el área principal
                yield StreamEvent(
                    event_type="token",
                    execution_id=execution_id,
                    node_id="",  # Sin node_id = respuesta final visible
                    content=response.content
                )
                
                yield StreamEvent(
                    event_type="node_end",
                    execution_id=execution_id,
                    node_id="sap_agent",
                    data={
                        "response": response.content,
                        "tools_used": [tr["tool"] for tr in tool_results],
                        "iterations": iteration
                    }
                )
                
                yield StreamEvent(
                    event_type="response_complete",
                    execution_id=execution_id,
                    node_id="sap_agent",
                    content=response.content,
                    data={
                        "tools_used": [tr["tool"] for tr in tool_results],
                        "iterations": iteration
                    }
                )
                
                # Resultado final para el executor
                yield {
                    "_result": {
                        "response": response.content,
                        "tools_used": [tr["tool"] for tr in tool_results],
                        "iterations": iteration
                    }
                }
                return
            
            # ========== CASO 2: TOOL CALLS ==========
            if response.tool_calls:
                num_tools = len(response.tool_calls)
                tool_names = [tc.function.get("name") for tc in response.tool_calls]
                
                logger.info(f"🔧 Processing {num_tools} tool call(s)")
                
                # Finalizar paso de análisis
                tools_list_short = ", ".join([name.replace("sap_btp_gateway_", "").replace("_", " ").title() for name in tool_names])
                yield StreamEvent(
                    event_type="token",
                    execution_id=execution_id,
                    node_id=analysis_node_id,
                    content=f"\n\n✅ Herramientas seleccionadas: {tools_list_short}"
                )
                
                yield StreamEvent(
                    event_type="node_end",
                    execution_id=execution_id,
                    node_id=analysis_node_id,
                    data={"tools_selected": tool_names}
                )
                
                # Agregar mensaje assistant con tool_calls (solo OpenAI/Anthropic)
                add_assistant_message_with_tool_calls(messages, response.tool_calls, provider_type)
                
                # Ejecutar cada tool call
                for idx, tool_call in enumerate(response.tool_calls, 1):
                    tool_name = tool_call.function.get("name")
                    tool_args_str = tool_call.function.get("arguments", "{}")
                    
                    # Parsear argumentos
                    try:
                        tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing tool arguments: {e}", args=tool_args_str)
                        tool_args = {}
                    
                    logger.info(f"🔧 Executing SAP tool: {tool_name}", args=tool_args)
                    
                    # Iniciar paso de ejecución de herramienta
                    tool_node_id = f"tool_{iteration}_{idx}"
                    tool_display_name = tool_name.replace("sap_btp_gateway_", "").replace("_", " ").title()
                    
                    yield StreamEvent(
                        event_type="node_start",
                        execution_id=execution_id,
                        node_id=tool_node_id,
                        node_name=f"⚙️ {tool_display_name}",
                        data={"tool": tool_name, "arguments": tool_args}
                    )
                    
                    # Mensaje visible: Ejecutando herramienta
                    yield StreamEvent(
                        event_type="token",
                        execution_id=execution_id,
                        node_id=tool_node_id,
                        content=f"Ejecutando consulta a SAP..."
                    )
                    
                    # Event: tool call iniciado (para compatibilidad)
                    yield StreamEvent(
                        event_type="tool_call",
                        execution_id=execution_id,
                        node_id=tool_node_id,
                        node_name=f"Tool: {tool_name}",
                        data={
                            "tool": tool_name,
                            "arguments": tool_args
                        }
                    )
                    
                    # Ejecutar herramienta SAP
                    try:
                        result = await execute_sap_tool(tool_name, tool_args)
                        
                        logger.info(
                            f"✅ SAP tool completed: {tool_name}",
                            success=result.get("success", False),
                            status_code=result.get("status_code"),
                            result_size=len(str(result))
                        )
                        
                        # Mensaje visible: Resultado obtenido
                        if result.get("success"):
                            data = result.get("data", {})
                            if isinstance(data, dict) and "users" in data:
                                count = len(data.get("users", []))
                                result_msg = f"\n\n✅ Datos recibidos: {count} usuarios"
                            elif isinstance(data, list):
                                result_msg = f"\n\n✅ Datos recibidos: {len(data)} registros"
                            else:
                                result_msg = f"\n\n✅ Datos recibidos correctamente"
                        else:
                            result_msg = f"\n\n❌ Error: {result.get('error', 'Unknown')}"
                        
                        yield StreamEvent(
                            event_type="token",
                            execution_id=execution_id,
                            node_id=tool_node_id,
                            content=result_msg
                        )
                        
                        # Finalizar paso de herramienta
                        yield StreamEvent(
                            event_type="node_end",
                            execution_id=execution_id,
                            node_id=tool_node_id,
                            data={
                                "success": result.get("success", False),
                                "status_code": result.get("status_code")
                            }
                        )
                        
                        tool_results.append({
                            "tool": tool_name,
                            "result": result
                        })
                        
                        # Event: tool result
                        yield StreamEvent(
                            event_type="tool_result",
                            execution_id=execution_id,
                            node_id="sap_agent",
                            data={
                                "tool": tool_name,
                                "success": result.get("success", False),
                                "data_preview": str(result.get("data", {}))[:500]
                            }
                        )
                        
                        # Agregar resultado al array de mensajes (formato específico por provider)
                        add_tool_result_message(messages, tool_call, result, provider_type)
                        
                    except Exception as e:
                        logger.error(f"❌ Error executing SAP tool {tool_name}: {e}", exc_info=True)
                        
                        error_result = {
                            "error": str(e),
                            "tool": tool_name,
                            "success": False
                        }
                        
                        tool_results.append({
                            "tool": tool_name,
                            "result": error_result
                        })
                        
                        # Agregar error al array de mensajes
                        add_tool_result_message(messages, tool_call, error_result, provider_type)
                
                # Iniciar paso de síntesis
                synthesis_node_id = f"synthesis_{iteration}"
                yield StreamEvent(
                    event_type="node_start",
                    execution_id=execution_id,
                    node_id=synthesis_node_id,
                    node_name="📊 Sintetizando respuesta",
                    data={"tools_executed": num_tools}
                )
                
                yield StreamEvent(
                    event_type="token",
                    execution_id=execution_id,
                    node_id=synthesis_node_id,
                    content="Generando respuesta con los datos obtenidos..."
                )
                
                yield StreamEvent(
                    event_type="node_end",
                    execution_id=execution_id,
                    node_id=synthesis_node_id,
                    data={}
                )
                
                # Continuar al siguiente turno (síntesis)
                logger.debug(f"Tool execution completed, continuing to next iteration")
                continue
            
            # ========== CASO 3: Sin content ni tool calls (error) ==========
            logger.warning("⚠️  LLM no generó tool calls ni content")
            break
                
        except Exception as e:
            logger.error(f"❌ Error in SAP Agent iteration {iteration}: {e}", exc_info=True)
            
            error_msg = f"Error al procesar consulta SAP: {str(e)}"
            
            yield StreamEvent(
                event_type="error",
                execution_id=execution_id,
                node_id="sap_agent",
                content=error_msg
            )
            break
    
    # ========== FALLBACK: Si llegamos aquí sin respuesta ==========
    logger.warning("⚠️  SAP Agent completed without final response")
    
    fallback_msg = "No se pudo generar respuesta con los datos SAP disponibles."
    
    yield StreamEvent(
        event_type="token",
        execution_id=execution_id,
        node_id="sap_agent",
        content=fallback_msg
    )
    
    yield StreamEvent(
        event_type="node_end",
        execution_id=execution_id,
        node_id="sap_agent",
        data={
            "response": fallback_msg,
            "tools_used": [tr["tool"] for tr in tool_results],
            "iterations": iteration,
            "fallback": True
        }
    )
    
    yield StreamEvent(
        event_type="response_complete",
        execution_id=execution_id,
        node_id="sap_agent",
        content=fallback_msg,
        data={
            "tools_used": [tr["tool"] for tr in tool_results],
            "iterations": iteration,
            "fallback": True
        }
    )
    
    # Resultado final para el executor
    yield {
        "_result": {
            "response": fallback_msg,
            "tools_used": [tr["tool"] for tr in tool_results],
            "iterations": iteration,
            "fallback": True
        }
    }


# ============================================
# Registro del Agente
# ============================================

def register_sap_agent():
    """Registrar el SAP Agent en el registry"""
    
    chain_registry.register(
        chain_id="sap_agent",
        definition=SAP_AGENT_DEFINITION,
        builder=build_sap_agent
    )
    
    logger.info("✅ SAP Agent registrado (v3.0.0 - Tool Calling Native)")
