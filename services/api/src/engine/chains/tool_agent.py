"""
Tool Agent - Agente con herramientas (REFACTORIZADO con estándar)
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
    build_llm_messages
)


# ============================================
# Funciones de herramientas
# ============================================

async def get_available_tools_description() -> str:
    """
    Obtener descripción de herramientas disponibles.
    Usa tool_registry para tener acceso a todas las herramientas.
    """
    # Obtener herramientas builtin (no OpenAPI para Tool Agent)
    builtin_tools = [t for t in tool_registry.tools.values() 
                     if t.type.value == "builtin"]
    
    if not builtin_tools:
        tool_registry.register_builtin_tools()
        builtin_tools = [t for t in tool_registry.tools.values() 
                        if t.type.value == "builtin"]
    
    descriptions = []
    for tool in builtin_tools[:20]:  # Limitar a 20 herramientas
        descriptions.append(f"- {tool.id}: {tool.description}")
    
    return "\n".join(descriptions)


async def execute_tool(tool_id: str, tool_input: str) -> str:
    """Ejecutar una herramienta via tool_registry"""
    try:
        result = await tool_registry.execute(tool_id, input=tool_input)
        return str(result.get("result", result))
    except Exception as e:
        return f"Error ejecutando {tool_id}: {str(e)}"


# ============================================
# Definición del Agente (con prompts editables)
# ============================================

TOOL_AGENT_DEFINITION = ChainDefinition(
    id="tool_agent",
    name="Tool Agent",
    description="Agente que puede usar herramientas para resolver tareas. Decide qué herramientas usar basándose en la pregunta.",
    type="tools",
    version="2.0.0",  # ✅ Versión actualizada
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
            # ✅ System prompt editable
            system_prompt="""Eres un agente que decide qué herramientas usar para responder preguntas.

HERRAMIENTAS DISPONIBLES:
{{tools_description}}

INSTRUCCIONES:
1. Analiza la pregunta del usuario
2. Decide si necesitas usar alguna herramienta
3. Si necesitas una herramienta, responde en formato JSON:
   {"tool": "nombre_herramienta", "input": "input para la herramienta"}
4. Si no necesitas herramientas, responde directamente

Responde SOLO con el JSON de la herramienta o con tu respuesta directa.""",
            prompt_template="{{user_query}}",
            temperature=0.3
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
            # ✅ System prompt editable
            system_prompt="""Genera una respuesta final basándote en los resultados de las herramientas.

RESULTADOS DE HERRAMIENTAS:
{{tool_results}}

PREGUNTA ORIGINAL: {{user_query}}

Proporciona una respuesta clara y útil.""",
            prompt_template="Genera la respuesta final.",
            temperature=0.7
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


# ============================================
# Builder Function (Lógica del Agente)
# ============================================

async def build_tool_agent(
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
    Builder del Tool Agent con herramientas builtin.
    
    FASES:
    1. Planning: Analizar query y decidir herramienta
    2. Tool Execution: Ejecutar herramienta si es necesario
    3. Synthesis: Formatear resultados en respuesta útil
    
    NODOS:
    - input (INPUT): Tarea del usuario
    - planner (LLM): Decide qué herramienta usar
    - tool_executor (TOOL): Ejecuta herramienta
    - synthesizer (LLM): Genera respuesta formateada
    - output (OUTPUT): Respuesta final
    
    MEMORY: Yes (últimos 10 mensajes)
    TOOLS: Builtin (calculator, current_time, web_search, etc.)
    """
    
    query = input_data.get("message", input_data.get("query", ""))
    
    # Cargar descripción de herramientas
    tools_description = await get_available_tools_description()
    
    # ✅ Obtener nodos con prompts editables
    planner_node = TOOL_AGENT_DEFINITION.get_node("planner")
    synthesizer_node = TOOL_AGENT_DEFINITION.get_node("synthesizer")
    
    if not planner_node or not synthesizer_node:
        raise ValueError("Nodos del Tool Agent no encontrados")
    
    # ========== FASE 1: PLANNING ==========
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="planner",
        node_name="Planificador",
        data={"analyzing": query}
    )
    
    # ✅ Construir mensajes con helper estándar
    planner_prompt = planner_node.system_prompt.replace("{{tools_description}}", tools_description)
    planner_messages = build_llm_messages(
        system_prompt=planner_prompt,
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
        node_name="Planificador",
        data={"decision": planner_response[:100]}
    )
    
    # ========== FASE 2: TOOL EXECUTION ==========
    tool_results = []
    tool_call = extract_json(planner_response)  # ✅ Usar helper compartido
    
    if tool_call and "tool" in tool_call:
        tool_id = tool_call.get("tool", "")
        tool_input = tool_call.get("input", "")
        
        yield StreamEvent(
            event_type="node_start",
            execution_id=execution_id,
            node_id="tool_executor",
            node_name=f"Ejecutando: {tool_id}",
            data={"tool": tool_id, "input": tool_input}
        )
        
        result = await execute_tool(tool_id, tool_input)
        tool_results.append({
            "tool": tool_id,
            "input": tool_input,
            "result": result
        })
        
        yield StreamEvent(
            event_type="node_end",
            execution_id=execution_id,
            node_id="tool_executor",
            node_name=f"Ejecutando: {tool_id}",
            data={"result": result[:200]}
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
        # Formatear resultados de herramientas
        results_json = json.dumps(tool_results, indent=2, ensure_ascii=False)
        
        # ✅ Construir mensajes con helper y reemplazar variables
        synth_prompt = synthesizer_node.system_prompt
        synth_prompt = synth_prompt.replace("{{tool_results}}", results_json)
        synth_prompt = synth_prompt.replace("{{user_query}}", query)
        
        synth_messages = build_llm_messages(
            system_prompt=synth_prompt,
            template=synthesizer_node.prompt_template,
            variables={},
            memory=None  # No incluir memoria en synthesis
        )
    else:
        # Sin herramientas: respuesta directa del planner
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
            system_prompt="Eres un asistente útil.",
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

def register_tool_agent():
    """Registrar el Tool Agent en el registry"""
    
    chain_registry.register(
        chain_id="tool_agent",
        definition=TOOL_AGENT_DEFINITION,
        builder=build_tool_agent
    )
