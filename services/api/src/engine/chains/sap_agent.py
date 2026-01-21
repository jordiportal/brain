"""
SAP Agent - Agente con herramientas SAP OpenAPI (REFACTORIZADO con estándar)
Soporta múltiples proveedores LLM: Ollama, OpenAI, Anthropic, etc.
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
from ...tools import tool_registry
from .llm_utils import call_llm, call_llm_stream
from .agent_helpers import (  # ✅ Usar helpers compartidos
    extract_json,
    build_llm_messages,
    format_json_preview
)


# ============================================
# Funciones de herramientas SAP
# ============================================

async def get_sap_tools_description() -> str:
    """
    Obtener descripción de herramientas SAP para el prompt.
    Esta función es específica del dominio SAP, no va en helpers.
    """
    sap_tools = [t for t in tool_registry.tools.values() 
                 if t.id.startswith("sap_btp_gateway")]
    
    if not sap_tools:
        await tool_registry.load_openapi_tools()
        sap_tools = [t for t in tool_registry.tools.values() 
                     if t.id.startswith("sap_btp_gateway")]
    
    descriptions = []
    for tool in sap_tools[:50]:
        params_str = ""
        if tool.openapi_tool and tool.openapi_tool.parameters:
            params = [f"{p.get('name')}({p.get('in', 'query')})" 
                     for p in tool.openapi_tool.parameters[:3]]
            if params:
                params_str = f" - Params: {', '.join(params)}"
        
        descriptions.append(f"- {tool.id}: {tool.description}{params_str}")
    
    return "\n".join(descriptions)


async def execute_sap_tool(tool_id: str, parameters: dict) -> dict:
    """Ejecutar una herramienta SAP via tool_registry"""
    return await tool_registry.execute(tool_id, **parameters)


# ============================================
# Definición del Agente (con prompts editables)
# ============================================

SAP_AGENT_DEFINITION = ChainDefinition(
    id="sap_agent",
    name="SAP Agent",
    description="Agente inteligente para consultar datos de SAP usando herramientas OpenAPI",
    type="tools",
    version="2.0.0",  # ✅ Versión actualizada
    nodes=[
        NodeDefinition(
            id="input",
            type=NodeType.INPUT,
            name="Consulta del usuario"
        ),
        NodeDefinition(
            id="planner",
            type=NodeType.LLM,
            name="Planificador SAP",
            # ✅ System prompt editable
            system_prompt="""Eres un asistente experto en SAP. Tu tarea es analizar la consulta del usuario y decidir qué herramienta usar.

HERRAMIENTAS SAP DISPONIBLES:
{{tools_description}}

INSTRUCCIONES:
1. Analiza qué información necesita el usuario
2. Selecciona la herramienta más apropiada
3. Responde SOLO con un JSON en este formato:
   {"tool": "nombre_herramienta", "parameters": {"param1": "valor1"}}

Si no necesitas herramientas, responde directamente con texto.
Si necesitas limitar resultados, usa el parámetro "limit" o "$top".

Ejemplos:
- Para pedidos de venta: {"tool": "sap_btp_gateway_get_api_sales-orders", "parameters": {"limit": 5}}
- Para productos: {"tool": "sap_btp_gateway_get_api_products", "parameters": {"limit": 10}}
- Para saldos bancarios: {"tool": "sap_btp_gateway_get_api_bank-balances_summary", "parameters": {}}""",
            # ✅ Template con variable
            prompt_template="{{user_query}}",
            temperature=0.2
        ),
        NodeDefinition(
            id="tool_executor",
            type=NodeType.TOOL,
            name="Ejecutor SAP"
        ),
        NodeDefinition(
            id="synthesizer",
            type=NodeType.LLM,
            name="Sintetizador",
            # ✅ System prompt editable
            system_prompt="""Genera una respuesta clara y útil basándote en los datos de SAP obtenidos.

DATOS DE SAP:
```json
{{sap_data}}
```

PREGUNTA ORIGINAL: {{user_query}}

INSTRUCCIONES:
- Formatea los datos de forma legible
- Si hay listas de items, usa tablas markdown
- Destaca los campos más relevantes
- {{truncation_warning}}
- Responde en español""",
            prompt_template="Genera la respuesta basándote en los datos.",
            temperature=0.7
        ),
        NodeDefinition(
            id="output",
            type=NodeType.OUTPUT,
            name="Respuesta"
        )
    ],
    config=ChainConfig(
        temperature=0.3,
        use_memory=True,
        max_memory_messages=6
    )
)


# ============================================
# Builder Function (Lógica del Agente)
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
    Builder del SAP Agent con herramientas OpenAPI.
    
    FASES:
    1. Planning: Analizar query y seleccionar herramienta SAP
    2. Tool Execution: Ejecutar herramienta si es necesario
    3. Synthesis: Formatear resultados en respuesta útil
    
    NODOS:
    - input (INPUT): Consulta del usuario
    - planner (LLM): Decide qué herramienta usar
    - tool_executor (TOOL): Ejecuta herramienta SAP
    - synthesizer (LLM): Genera respuesta formateada
    - output (OUTPUT): Respuesta final
    
    MEMORY: Yes (últimos 6 mensajes)
    TOOLS: OpenAPI SAP (dinámicas desde Strapi)
    """
    
    query = input_data.get("message", input_data.get("query", ""))
    
    # Cargar descripción de herramientas SAP
    tools_description = await get_sap_tools_description()
    
    # ✅ Obtener nodos con prompts editables
    planner_node = SAP_AGENT_DEFINITION.get_node("planner")
    synthesizer_node = SAP_AGENT_DEFINITION.get_node("synthesizer")
    
    if not planner_node or not synthesizer_node:
        raise ValueError("Nodos del SAP Agent no encontrados")
    
    # ========== FASE 1: PLANNING ==========
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="planner",
        node_name="Planificador SAP",
        data={"analyzing": query}
    )
    
    # ✅ Construir mensajes con helper estándar
    planner_messages = build_llm_messages(
        system_prompt=planner_node.system_prompt.replace("{{tools_description}}", tools_description),
        template=planner_node.prompt_template,
        variables={"user_query": query},
        memory=memory,
        max_memory=config.max_memory_messages
    )
    
    planner_response = await call_llm(
        llm_url, model, planner_messages,
        temperature=planner_node.temperature,
        provider_type=provider_type,
        api_key=api_key
    )
    
    yield StreamEvent(
        event_type="node_end",
        execution_id=execution_id,
        node_id="planner",
        node_name="Planificador SAP",
        data={"decision": planner_response[:200]}
    )
    
    # ========== FASE 2: TOOL EXECUTION ==========
    tool_results = []
    tool_call = extract_json(planner_response)  # ✅ Usar helper compartido
    
    if tool_call and "tool" in tool_call:
        tool_id = tool_call.get("tool", "")
        parameters = tool_call.get("parameters", {})
        
        yield StreamEvent(
            event_type="node_start",
            execution_id=execution_id,
            node_id="tool_executor",
            node_name=f"Ejecutando: {tool_id}",
            data={"tool": tool_id, "parameters": parameters}
        )
        
        result = await execute_sap_tool(tool_id, parameters)
        tool_results.append({
            "tool": tool_id,
            "parameters": parameters,
            "result": result
        })
        
        yield StreamEvent(
            event_type="node_end",
            execution_id=execution_id,
            node_id="tool_executor",
            node_name=f"Ejecutando: {tool_id}",
            data={
                "success": result.get("success", False),
                "status_code": result.get("status_code"),
                "data_preview": str(result.get("data", {}))[:500]
            }
        )
    
    # ========== FASE 3: SYNTHESIS ==========
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="synthesizer",
        node_name="Sintetizador",
        data={"generating": True}
    )
    
    if tool_results:
        # Formatear datos de SAP
        tool_data = tool_results[0].get("result", {}).get("data", {})
        
        # ✅ Usar helper para formateo con truncado
        json_preview, data_truncated = format_json_preview(tool_data, max_chars=15000)
        
        truncation_msg = (
            "⚠️ IMPORTANTE: Los datos están TRUNCADOS. Indica al usuario que hay más registros disponibles."
            if data_truncated else "Los datos están completos."
        )
        
        # ✅ Construir mensajes con helper y reemplazar variables
        synth_prompt = synthesizer_node.system_prompt
        synth_prompt = synth_prompt.replace("{{sap_data}}", json_preview)
        synth_prompt = synth_prompt.replace("{{user_query}}", query)
        synth_prompt = synth_prompt.replace("{{truncation_warning}}", truncation_msg)
        
        synth_messages = build_llm_messages(
            system_prompt=synth_prompt,
            template=synthesizer_node.prompt_template,
            variables={},
            memory=None  # No incluir memoria en synthesis
        )
    else:
        # Sin herramientas: respuesta directa
        if not planner_response.strip().startswith("{"):
            # Es una respuesta conversacional directa
            if stream:
                for char in planner_response:
                    yield StreamEvent(
                        event_type="token",
                        execution_id=execution_id,
                        node_id="synthesizer",
                        content=char
                    )
            
            yield StreamEvent(
                event_type="node_end",
                execution_id=execution_id,
                node_id="synthesizer",
                node_name="Sintetizador",
                data={"response": planner_response}
            )
            
            if not stream:
                yield {"_result": {
                    "response": planner_response,
                    "tools_used": [],
                    "tool_results": []
                }}
            return
        
        # Fallback: respuesta simple
        synth_messages = build_llm_messages(
            system_prompt="Eres un asistente experto en SAP. Responde de forma clara y útil.",
            template="{{user_query}}",
            variables={"user_query": query},
            memory=None
        )
    
    # Streaming de respuesta final
    full_response = ""
    async for token in call_llm_stream(
        llm_url, model, synth_messages,
        temperature=synthesizer_node.temperature,
        provider_type=provider_type,
        api_key=api_key
    ):
        full_response += token
        yield StreamEvent(
            event_type="token",
            execution_id=execution_id,
            node_id="synthesizer",
            content=token
        )
    
    yield StreamEvent(
        event_type="node_end",
        execution_id=execution_id,
        node_id="synthesizer",
        node_name="Sintetizador",
        data={
            "response": full_response[:500],
            "tools_used": [t["tool"] for t in tool_results]
        }
    )
    
    # Para modo no-streaming
    if not stream:
        yield {"_result": {
            "response": full_response,
            "tools_used": [t["tool"] for t in tool_results],
            "tool_results": tool_results
        }}


# ============================================
# Registro del Agente
# ============================================

def register_sap_agent():
    """Registrar el agente SAP en el registry"""
    
    chain_registry.register(
        chain_id="sap_agent",
        definition=SAP_AGENT_DEFINITION,
        builder=build_sap_agent
    )
