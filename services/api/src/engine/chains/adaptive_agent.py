"""
Brain 2.0 Adaptive Agent - Agente principal con razonamiento adaptativo

Este es el ÚNICO agente de Brain 2.0. Usa las 15 core tools y ajusta
su modo de razonamiento según la complejidad de la tarea.

Flujo:
1. Analizar query → Detectar complejidad
2. Seleccionar modo de razonamiento (NONE, INTERNAL, EXTENDED)
3. Loop de ejecución con tools
4. Respuesta final via tool "finish"
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
from ..reasoning import (
    detect_complexity,
    get_reasoning_config,
    ComplexityLevel,
    ReasoningMode
)
from ...tools import tool_registry
from .llm_utils import call_llm_with_tools, LLMToolResponse, ToolCall

import structlog

logger = structlog.get_logger()


# ============================================
# System Prompt
# ============================================

ADAPTIVE_AGENT_SYSTEM_PROMPT = """You are Brain 2.0, an intelligent assistant with access to tools.

# CORE PRINCIPLES

1. **THINK BEFORE ACT**: For complex tasks, use the `think` tool to plan your approach.
2. **USE TOOLS**: You have powerful tools available. Use them to accomplish tasks.
3. **REFLECT ON RESULTS**: After using tools, evaluate if you achieved the goal.
4. **FINISH WITH ANSWER**: Always use the `finish` tool to provide your final answer.

# AVAILABLE TOOLS

## Filesystem
- `read`: Read file contents
- `write`: Create/overwrite files
- `edit`: Edit files (replace text)
- `list`: List directory contents
- `search`: Search files or content

## Execution
- `shell`: Execute shell commands
- `python`: Run Python code in Docker
- `javascript`: Run JavaScript in Docker

## Web
- `web_search`: Search the internet
- `web_fetch`: Fetch URL content

## Reasoning (Meta-tools)
- `think`: Plan and reason about the task
- `reflect`: Evaluate results and progress
- `plan`: Create structured plan for complex tasks
- `finish`: Provide final answer to user

## Utils
- `calculate`: Evaluate math expressions

# WORKFLOW

{workflow_instructions}

# IMPORTANT

- ALWAYS end with the `finish` tool containing your complete answer
- Use markdown formatting in your final answer when appropriate
- If a tool fails, try an alternative approach
- Be concise but thorough

Now, help the user with their request."""

WORKFLOW_SIMPLE = """For this SIMPLE task:
1. Directly use the appropriate tool(s)
2. Use `finish` to provide your answer"""

WORKFLOW_MODERATE = """For this MODERATE task:
1. Optionally use `think` to plan your approach
2. Use tools to gather information or perform actions
3. Optionally use `reflect` to evaluate progress
4. Use `finish` to provide your answer"""

WORKFLOW_COMPLEX = """For this COMPLEX task:
1. Use `plan` to create a structured approach
2. Use `think` before each major step
3. Execute tools according to your plan
4. Use `reflect` after getting results
5. Iterate until the task is complete
6. Use `finish` to provide your comprehensive answer"""


# ============================================
# Chain Definition
# ============================================

ADAPTIVE_AGENT_DEFINITION = ChainDefinition(
    id="adaptive",
    name="Brain 2.0 Adaptive Agent",
    description="Agente inteligente con razonamiento adaptativo y 15 core tools",
    type="agent",
    version="2.0.0",
    nodes=[
        NodeDefinition(
            id="adaptive_agent",
            type=NodeType.LLM,
            name="Adaptive Agent",
            system_prompt=ADAPTIVE_AGENT_SYSTEM_PROMPT,
            temperature=0.5
        )
    ],
    config=ChainConfig(
        temperature=0.5,
        use_memory=True,
        max_memory_messages=10
    )
)


# ============================================
# Builder Function
# ============================================

async def build_adaptive_agent(
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
    Builder del Adaptive Agent de Brain 2.0.
    
    Flujo:
    1. Detectar complejidad de la query
    2. Configurar modo de razonamiento
    3. Loop de tool calling hasta finish
    """
    
    query = input_data.get("message", input_data.get("query", ""))
    
    logger.info(
        "🧠 Brain 2.0 Adaptive Agent starting",
        query=query[:100],
        model=model,
        provider=provider_type
    )
    
    # ========== FASE 1: ANÁLISIS DE COMPLEJIDAD ==========
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="complexity_analysis",
        node_name="Analyzing task complexity",
        data={"query": query[:100]}
    )
    
    # Detectar complejidad
    complexity_analysis = detect_complexity(query)
    reasoning_config = get_reasoning_config(complexity_analysis.level)
    
    yield StreamEvent(
        event_type="node_end",
        execution_id=execution_id,
        node_id="complexity_analysis",
        data={
            "complexity": complexity_analysis.level.value,
            "reasoning_mode": reasoning_config.mode.value,
            "estimated_tools": complexity_analysis.estimated_tools
        }
    )
    
    # Seleccionar workflow según complejidad
    if complexity_analysis.level == ComplexityLevel.COMPLEX:
        workflow = WORKFLOW_COMPLEX
    elif complexity_analysis.level == ComplexityLevel.MODERATE:
        workflow = WORKFLOW_MODERATE
    else:
        workflow = WORKFLOW_SIMPLE
    
    # ========== FASE 2: PREPARAR TOOLS Y MENSAJES ==========
    
    # Registrar core tools si no están registradas
    tool_registry.register_core_tools()
    
    # Obtener tools en formato LLM
    tools = tool_registry.get_tools_for_llm()
    
    logger.info(f"📦 {len(tools)} core tools loaded")
    
    # Construir system prompt
    system_prompt = ADAPTIVE_AGENT_SYSTEM_PROMPT.format(
        workflow_instructions=workflow
    )
    
    # Construir mensajes con memoria
    messages = [{"role": "system", "content": system_prompt}]
    
    # Agregar memoria (últimos N mensajes)
    if memory and config.use_memory:
        max_memory = config.max_memory_messages or 10
        for msg in memory[-max_memory:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
    
    # Agregar query actual
    messages.append({"role": "user", "content": query})
    
    # ========== FASE 3: LOOP DE TOOL CALLING ==========
    
    max_iterations = reasoning_config.max_iterations
    tool_results = []
    iteration = 0
    final_answer = None
    
    while iteration < max_iterations:
        iteration += 1
        
        yield StreamEvent(
            event_type="node_start",
            execution_id=execution_id,
            node_id=f"iteration_{iteration}",
            node_name=f"Iteration {iteration}/{max_iterations}",
            data={"iteration": iteration}
        )
        
        try:
            # Llamar al LLM con tools
            response: LLMToolResponse = await call_llm_with_tools(
                llm_url=llm_url,
                model=model,
                messages=messages,
                tools=tools,
                temperature=reasoning_config.temperature,
                provider_type=provider_type,
                api_key=api_key
            )
            
            # ========== CASO 1: SOLO CONTENIDO (sin tools) ==========
            if response.content and not response.tool_calls:
                logger.info(f"📝 LLM provided direct response (iteration {iteration})")
                
                # Si el modelo responde sin usar finish, tratarlo como respuesta final
                final_answer = response.content
                
                yield StreamEvent(
                    event_type="token",
                    execution_id=execution_id,
                    node_id="",
                    content=response.content
                )
                
                yield StreamEvent(
                    event_type="node_end",
                    execution_id=execution_id,
                    node_id=f"iteration_{iteration}",
                    data={"direct_response": True}
                )
                break
            
            # ========== CASO 2: TOOL CALLS ==========
            if response.tool_calls:
                # Agregar mensaje del assistant con tool_calls
                if provider_type != "ollama":
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
                        } for tc in response.tool_calls]
                    })
                
                # Ejecutar cada tool
                for tool_call in response.tool_calls:
                    tool_name = tool_call.function.get("name")
                    tool_args_str = tool_call.function.get("arguments", "{}")
                    
                    # Parsear argumentos
                    try:
                        tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                    except json.JSONDecodeError:
                        tool_args = {}
                    
                    logger.info(f"🔧 Executing tool: {tool_name}", args=list(tool_args.keys()))
                    
                    # Yield evento de tool call
                    yield StreamEvent(
                        event_type="tool_call",
                        execution_id=execution_id,
                        node_id=f"tool_{tool_name}",
                        node_name=f"Tool: {tool_name}",
                        data={"tool": tool_name, "arguments": tool_args}
                    )
                    
                    # Ejecutar tool
                    result = await tool_registry.execute(tool_name, **tool_args)
                    
                    # Verificar si es finish
                    if tool_name == "finish":
                        final_answer = result.get("final_answer", "")
                        
                        yield StreamEvent(
                            event_type="tool_result",
                            execution_id=execution_id,
                            node_id=f"tool_{tool_name}",
                            data={"tool": tool_name, "done": True}
                        )
                        
                        # Emitir respuesta final
                        yield StreamEvent(
                            event_type="token",
                            execution_id=execution_id,
                            node_id="",
                            content=final_answer
                        )
                        break
                    
                    # Guardar resultado
                    tool_results.append({
                        "tool": tool_name,
                        "result": result
                    })
                    
                    yield StreamEvent(
                        event_type="tool_result",
                        execution_id=execution_id,
                        node_id=f"tool_{tool_name}",
                        data={
                            "tool": tool_name,
                            "success": result.get("success", False),
                            "preview": str(result)[:200]
                        }
                    )
                    
                    # Agregar resultado a mensajes
                    result_str = json.dumps(result, ensure_ascii=False, default=str)
                    if len(result_str) > 4000:
                        result_str = result_str[:4000] + "... [truncated]"
                    
                    if provider_type == "ollama":
                        messages.append({
                            "role": "tool",
                            "content": result_str
                        })
                    else:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": result_str
                        })
                
                # Si encontramos finish, salir del loop
                if final_answer is not None:
                    yield StreamEvent(
                        event_type="node_end",
                        execution_id=execution_id,
                        node_id=f"iteration_{iteration}",
                        data={"finished": True}
                    )
                    break
            
            yield StreamEvent(
                event_type="node_end",
                execution_id=execution_id,
                node_id=f"iteration_{iteration}",
                data={"tools_used": len(response.tool_calls) if response.tool_calls else 0}
            )
            
        except Exception as e:
            logger.error(f"Error in iteration {iteration}: {e}", exc_info=True)
            
            yield StreamEvent(
                event_type="error",
                execution_id=execution_id,
                node_id=f"iteration_{iteration}",
                content=f"Error: {str(e)}"
            )
            
            # Continuar al siguiente intento
            continue
    
    # ========== FASE 4: FINALIZACIÓN ==========
    
    if final_answer is None:
        # Si no se obtuvo respuesta, generar una de fallback
        final_answer = "No se pudo completar la tarea. Por favor, reformula tu petición."
        
        yield StreamEvent(
            event_type="token",
            execution_id=execution_id,
            node_id="",
            content=final_answer
        )
    
    # Evento de completado
    yield StreamEvent(
        event_type="response_complete",
        execution_id=execution_id,
        node_id="adaptive_agent",
        content=final_answer,
        data={
            "complexity": complexity_analysis.level.value,
            "iterations": iteration,
            "tools_used": [tr["tool"] for tr in tool_results]
        }
    )
    
    # Resultado para el executor
    yield {
        "_result": {
            "response": final_answer,
            "complexity": complexity_analysis.level.value,
            "reasoning_mode": reasoning_config.mode.value,
            "iterations": iteration,
            "tools_used": [tr["tool"] for tr in tool_results]
        }
    }


# ============================================
# Registro del Agente
# ============================================

def register_adaptive_agent():
    """Registrar el Adaptive Agent en el registry"""
    
    chain_registry.register(
        chain_id="adaptive",
        definition=ADAPTIVE_AGENT_DEFINITION,
        builder=build_adaptive_agent
    )
    
    logger.info("✅ Brain 2.0 Adaptive Agent registered (v2.0.0)")
