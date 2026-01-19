"""
Tool Agent - Agente con herramientas
"""

import json
from typing import AsyncGenerator, Optional, Callable
import httpx
from datetime import datetime

from ..models import (
    ChainDefinition,
    ChainConfig,
    NodeDefinition,
    NodeType,
    ExecutionState,
    ExecutionStep,
    StreamEvent
)
from ..registry import chain_registry


# NOTA: Las herramientas ahora están centralizadas en tool_registry
# Este archivo mantiene DEFAULT_TOOLS para compatibilidad con código legacy,
# pero se recomienda usar tool_registry directamente.

# Herramientas disponibles por defecto (LEGACY - usar tool_registry)
DEFAULT_TOOLS = {
    "calculator": {
        "name": "calculator",
        "description": "Realiza cálculos matemáticos. Input: expresión matemática como string.",
        "handler": lambda expr: str(eval(expr))  # LEGACY: usar tool_registry.calculator
    },
    "current_time": {
        "name": "current_time",
        "description": "Obtiene la fecha y hora actual.",
        "handler": lambda _: datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # LEGACY
    },
    "web_search": {
        "name": "web_search",
        "description": "Busca información en la web usando DuckDuckGo.",
        "handler": lambda query: {"info": "Usar tool_registry.web_search para búsquedas reales"}
    }
}


# Definición de la cadena
TOOL_AGENT = ChainDefinition(
    id="tool_agent",
    name="Tool Agent",
    description="Agente que puede usar herramientas para resolver tareas. Decide qué herramientas usar basándose en la pregunta.",
    type="tools",
    version="1.0.0",
    nodes=[
        NodeDefinition(
            id="input",
            type=NodeType.INPUT,
            name="Tarea del usuario"
        ),
        NodeDefinition(
            id="planner",
            type=NodeType.LLM,
            name="Planificador",
            system_prompt="""Eres un agente que decide qué herramientas usar para responder preguntas.

HERRAMIENTAS DISPONIBLES:
{tools}

INSTRUCCIONES:
1. Analiza la pregunta del usuario
2. Decide si necesitas usar alguna herramienta
3. Si necesitas una herramienta, responde en formato JSON:
   {{"tool": "nombre_herramienta", "input": "input para la herramienta"}}
4. Si no necesitas herramientas, responde directamente

Responde SOLO con el JSON de la herramienta o con tu respuesta directa."""
        ),
        NodeDefinition(
            id="tool_executor",
            type=NodeType.TOOL,
            name="Ejecutor de herramientas"
        ),
        NodeDefinition(
            id="synthesizer",
            type=NodeType.LLM,
            name="Sintetizador",
            system_prompt="""Genera una respuesta final basándote en los resultados de las herramientas.
            
Resultados de herramientas: {tool_results}

Pregunta original: {original_question}

Proporciona una respuesta clara y útil."""
        ),
        NodeDefinition(
            id="output",
            type=NodeType.OUTPUT,
            name="Respuesta final"
        )
    ],
    config=ChainConfig(
        use_memory=True,
        max_memory_messages=10,
        temperature=0.5
    )
)


def get_tools_description(tools: dict) -> str:
    """Generar descripción de herramientas para el prompt"""
    descriptions = []
    for name, tool in tools.items():
        descriptions.append(f"- {name}: {tool['description']}")
    return "\n".join(descriptions)


async def execute_tool(tool_name: str, tool_input: str, tools: dict) -> str:
    """Ejecutar una herramienta"""
    if tool_name not in tools:
        return f"Error: Herramienta '{tool_name}' no encontrada"
    
    try:
        handler = tools[tool_name]["handler"]
        result = handler(tool_input)
        return str(result)
    except Exception as e:
        return f"Error ejecutando {tool_name}: {str(e)}"


async def build_tool_agent(
    config: ChainConfig,
    llm_url: str,
    model: str,
    input_data: dict,
    memory: list,
    execution_id: str = "",
    execution_state: Optional[ExecutionState] = None,
    stream: bool = False,
    tools: dict = None,
    **kwargs
):
    """Builder del agente con herramientas"""
    
    if tools is None:
        tools = DEFAULT_TOOLS
    
    query = input_data.get("message", input_data.get("query", ""))
    tools_description = get_tools_description(tools)
    
    if stream:
        # Paso 1: Planificación
        yield StreamEvent(
            event_type="node_start",
            execution_id=execution_id,
            node_id="planner",
            node_name="Planificador",
            data={"analyzing": query}
        )
        
        planner_prompt = TOOL_AGENT.nodes[1].system_prompt.format(tools=tools_description)
        
        messages = [
            {"role": "system", "content": planner_prompt},
            {"role": "user", "content": query}
        ]
        
        planner_response = ""
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{llm_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.3}
                }
            )
            data = response.json()
            planner_response = data.get("message", {}).get("content", "")
        
        yield StreamEvent(
            event_type="node_end",
            execution_id=execution_id,
            node_id="planner",
            node_name="Planificador",
            data={"decision": planner_response[:100]}
        )
        
        # Intentar parsear como JSON de herramienta
        tool_results = []
        try:
            tool_call = json.loads(planner_response)
            if "tool" in tool_call:
                # Ejecutar herramienta
                yield StreamEvent(
                    event_type="node_start",
                    execution_id=execution_id,
                    node_id="tool_executor",
                    node_name=f"Ejecutando: {tool_call['tool']}",
                    data={"tool": tool_call["tool"], "input": tool_call.get("input", "")}
                )
                
                result = await execute_tool(
                    tool_call["tool"],
                    tool_call.get("input", ""),
                    tools
                )
                tool_results.append({
                    "tool": tool_call["tool"],
                    "result": result
                })
                
                yield StreamEvent(
                    event_type="node_end",
                    execution_id=execution_id,
                    node_id="tool_executor",
                    node_name=f"Ejecutando: {tool_call['tool']}",
                    data={"result": result}
                )
        except json.JSONDecodeError:
            # No es JSON, es respuesta directa
            pass
        
        # Paso 3: Sintetizar respuesta
        yield StreamEvent(
            event_type="node_start",
            execution_id=execution_id,
            node_id="synthesizer",
            node_name="Sintetizador",
            data={"generating": True}
        )
        
        if tool_results:
            synth_prompt = TOOL_AGENT.nodes[3].system_prompt.format(
                tool_results=json.dumps(tool_results, ensure_ascii=False),
                original_question=query
            )
            messages = [
                {"role": "system", "content": synth_prompt},
                {"role": "user", "content": "Genera la respuesta final."}
            ]
        else:
            # Usar respuesta del planificador directamente
            messages = [
                {"role": "system", "content": "Eres un asistente útil."},
                {"role": "user", "content": query}
            ]
            if planner_response and not planner_response.startswith("{"):
                # Ya tenemos respuesta directa
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
                return
        
        # Streaming de respuesta final
        full_response = ""
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{llm_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    "options": {"temperature": config.temperature}
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                full_response += content
                                yield StreamEvent(
                                    event_type="token",
                                    execution_id=execution_id,
                                    node_id="synthesizer",
                                    content=content
                                )
                        except json.JSONDecodeError:
                            continue
        
        yield StreamEvent(
            event_type="node_end",
            execution_id=execution_id,
            node_id="synthesizer",
            node_name="Sintetizador",
            data={"response": full_response, "tools_used": [t["tool"] for t in tool_results]}
        )
    
    else:
        # Sin streaming - implementación simplificada
        planner_prompt = TOOL_AGENT.nodes[1].system_prompt.format(tools=tools_description)
        
        messages = [
            {"role": "system", "content": planner_prompt},
            {"role": "user", "content": query}
        ]
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{llm_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0.3}
                }
            )
            data = response.json()
            planner_response = data.get("message", {}).get("content", "")
        
        tool_results = []
        try:
            tool_call = json.loads(planner_response)
            if "tool" in tool_call:
                result = await execute_tool(
                    tool_call["tool"],
                    tool_call.get("input", ""),
                    tools
                )
                tool_results.append({
                    "tool": tool_call["tool"],
                    "result": result
                })
        except json.JSONDecodeError:
            pass
        
        if tool_results:
            synth_prompt = TOOL_AGENT.nodes[3].system_prompt.format(
                tool_results=json.dumps(tool_results, ensure_ascii=False),
                original_question=query
            )
            messages = [
                {"role": "system", "content": synth_prompt},
                {"role": "user", "content": "Genera la respuesta final."}
            ]
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{llm_url}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False,
                        "options": {"temperature": config.temperature}
                    }
                )
                data = response.json()
                final_response = data.get("message", {}).get("content", "")
        else:
            final_response = planner_response
        
        yield {"_result": {
            "response": final_response,
            "tools_used": [t["tool"] for t in tool_results],
            "tool_results": tool_results
        }}


def register_tool_agent():
    """Registrar el agente con herramientas"""
    chain_registry.register(
        chain_id="tool_agent",
        definition=TOOL_AGENT,
        builder=build_tool_agent
    )
