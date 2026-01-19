"""
SAP Agent - Agente con herramientas SAP OpenAPI
Soporta múltiples proveedores LLM: Ollama, OpenAI, Anthropic, etc.
"""

import json
import re
from typing import AsyncGenerator, Optional
from datetime import datetime

from ..models import (
    ChainConfig,
    StreamEvent
)
from ..registry import chain_registry
from ...tools import tool_registry, openapi_toolkit
from .llm_utils import call_llm, call_llm_stream


async def get_sap_tools_description() -> str:
    """Obtener descripción de herramientas SAP para el prompt"""
    # Asegurar que las herramientas están cargadas
    if not openapi_toolkit.tools:
        await openapi_toolkit.load_all_tools()
    
    # Filtrar herramientas SAP
    sap_tools = [t for t in openapi_toolkit.tools.values() 
                 if t.id.startswith("sap_btp_gateway")]
    
    descriptions = []
    for tool in sap_tools[:30]:  # Limitar para no sobrecargar el prompt
        params_str = ""
        if tool.parameters:
            params = [f"{p.get('name')}({p.get('in', 'query')})" 
                     for p in tool.parameters[:3]]
            if params:
                params_str = f" - Params: {', '.join(params)}"
        
        descriptions.append(f"- {tool.id}: {tool.description}{params_str}")
    
    return "\n".join(descriptions)


async def execute_sap_tool(tool_id: str, parameters: dict) -> dict:
    """Ejecutar una herramienta SAP"""
    tool = openapi_toolkit.get_tool(tool_id)
    if not tool:
        return {"error": f"Herramienta no encontrada: {tool_id}"}
    
    return await tool.execute(**parameters)


def extract_tool_call(response: str) -> Optional[dict]:
    """Extraer llamada a herramienta del texto del LLM"""
    # Buscar JSON en la respuesta
    json_patterns = [
        r'\{[^{}]*"tool"[^{}]*\}',
        r'```json\s*(\{.*?\})\s*```',
        r'```\s*(\{.*?\})\s*```'
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, response, re.DOTALL)
        for match in matches:
            try:
                data = json.loads(match if isinstance(match, str) else match)
                if "tool" in data:
                    return data
            except json.JSONDecodeError:
                continue
    
    # Intentar parsear toda la respuesta como JSON
    try:
        data = json.loads(response.strip())
        if "tool" in data:
            return data
    except json.JSONDecodeError:
        pass
    
    return None


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
):
    """Builder del agente SAP con herramientas OpenAPI"""
    
    query = input_data.get("message", input_data.get("query", ""))
    
    # Cargar herramientas SAP
    tools_description = await get_sap_tools_description()
    
    # === PASO 1: Planificación ===
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="planner",
        node_name="Planificador SAP",
        data={"analyzing": query}
    )
    
    planner_prompt = f"""Eres un asistente experto en SAP. Tu tarea es analizar la consulta del usuario y decidir qué herramienta usar.

HERRAMIENTAS SAP DISPONIBLES:
{tools_description}

INSTRUCCIONES:
1. Analiza qué información necesita el usuario
2. Selecciona la herramienta más apropiada
3. Responde SOLO con un JSON en este formato:
   {{"tool": "nombre_herramienta", "parameters": {{"param1": "valor1"}}}}

Si no necesitas herramientas, responde directamente con texto.
Si necesitas limitar resultados, usa el parámetro "limit" o "$top".

Ejemplos:
- Para pedidos de venta: {{"tool": "sap_btp_gateway_get_api_sales-orders", "parameters": {{"limit": 5}}}}
- Para productos: {{"tool": "sap_btp_gateway_get_api_products", "parameters": {{"limit": 10}}}}
- Para saldos bancarios: {{"tool": "sap_btp_gateway_get_api_bank-balances_summary", "parameters": {{}}}}"""

    messages = [
        {"role": "system", "content": planner_prompt}
    ]
    
    # Añadir memoria si existe
    for msg in memory[-6:]:  # Últimos 6 mensajes
        messages.append(msg)
    
    messages.append({"role": "user", "content": query})
    
    planner_response = await call_llm(
        llm_url, model, messages,
        temperature=0.2,
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
    
    # === PASO 2: Ejecutar herramienta si es necesario ===
    tool_results = []
    tool_call = extract_tool_call(planner_response)
    
    if tool_call:
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
    
    # === PASO 3: Sintetizar respuesta ===
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="synthesizer",
        node_name="Sintetizador",
        data={"generating": True}
    )
    
    if tool_results:
        # Formatear resultados para el sintetizador
        tool_data = tool_results[0].get("result", {}).get("data", {})
        
        synth_prompt = f"""Genera una respuesta clara y útil basándote en los datos de SAP obtenidos.

DATOS DE SAP:
```json
{json.dumps(tool_data, indent=2, ensure_ascii=False, default=str)[:4000]}
```

PREGUNTA ORIGINAL: {query}

INSTRUCCIONES:
- Formatea los datos de forma legible
- Si hay listas de items, usa tablas markdown
- Destaca los campos más relevantes
- Si los datos están truncados, indícalo
- Responde en español"""

        messages = [
            {"role": "system", "content": synth_prompt},
            {"role": "user", "content": "Genera la respuesta basándote en los datos."}
        ]
    else:
        # Sin herramientas, usar respuesta directa
        if not planner_response.strip().startswith("{"):
            # Es una respuesta directa
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
            
            # Para modo no-streaming
            if not stream:
                yield {"_result": {
                    "response": planner_response,
                    "tools_used": [],
                    "tool_results": []
                }}
            return
        
        messages = [
            {"role": "system", "content": "Eres un asistente experto en SAP. Responde de forma clara y útil."},
            {"role": "user", "content": query}
        ]
    
    # Streaming de respuesta final
    full_response = ""
    async for token in call_llm_stream(
        llm_url, model, messages,
        temperature=config.temperature,
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
    
    # Para modo no-streaming, devolver resultado final
    if not stream:
        yield {"_result": {
            "response": full_response,
            "tools_used": [t["tool"] for t in tool_results],
            "tool_results": tool_results
        }}


def register_sap_agent():
    """Registrar el agente SAP"""
    from ..models import ChainDefinition, NodeDefinition, NodeType, ChainConfig
    
    definition = ChainDefinition(
        id="sap_agent",
        name="SAP Agent",
        description="Agente inteligente para consultar datos de SAP usando herramientas OpenAPI",
        type="tools",
        version="1.0.0",
        nodes=[
            NodeDefinition(id="input", type=NodeType.INPUT, name="Consulta"),
            NodeDefinition(id="planner", type=NodeType.LLM, name="Planificador SAP"),
            NodeDefinition(id="tool_executor", type=NodeType.TOOL, name="Ejecutor SAP"),
            NodeDefinition(id="synthesizer", type=NodeType.LLM, name="Sintetizador"),
            NodeDefinition(id="output", type=NodeType.OUTPUT, name="Respuesta")
        ],
        config=ChainConfig(temperature=0.3, use_memory=True)
    )
    
    chain_registry.register(
        chain_id="sap_agent",
        definition=definition,
        builder=build_sap_agent
    )
