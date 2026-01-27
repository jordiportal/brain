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
# Validación de Tool Names
# ============================================

# Lista de tools válidas
VALID_TOOL_NAMES = {
    "read", "write", "edit", "list", "search",
    "shell", "python", "javascript",
    "web_search", "web_fetch",
    "think", "reflect", "plan", "finish",
    "calculate"
}

def is_valid_tool_name(name: str) -> bool:
    """
    Validar que el nombre de la tool es válido.
    Filtra artifacts de modelos como 'assistant<|channel|>commentary'
    """
    if not name:
        return False
    
    # Patrones inválidos (artifacts de modelos)
    invalid_patterns = ['<|', '|>', 'channel', 'functions<', 'assistant<']
    for pattern in invalid_patterns:
        if pattern in name.lower():
            return False
    
    # Verificar que está en la lista de tools válidas
    return name.lower() in VALID_TOOL_NAMES


# ============================================
# System Prompt
# ============================================

ADAPTIVE_AGENT_SYSTEM_PROMPT = """You are Brain 2.0, an intelligent assistant with access to tools.

# CORE PRINCIPLES

1. **THINK BEFORE ACT**: For complex tasks, use the `think` tool to plan your approach.
2. **USE TOOLS**: You have powerful tools available. Use them to accomplish tasks.
3. **REFLECT ON RESULTS**: After using tools, evaluate if you achieved the goal.
4. **FINISH WITH ANSWER**: You MUST ALWAYS use the `finish` tool to provide your final answer.

# AVAILABLE TOOLS

## Filesystem
- `read`: Read file contents
- `write`: Create/overwrite files (ALWAYS use this when asked to save something)
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
- `finish`: Provide final answer to user - YOU MUST CALL THIS TO COMPLETE

## Utils
- `calculate`: Evaluate math expressions

# WORKFLOW

{workflow_instructions}

# CRITICAL RULES - FOLLOW THESE EXACTLY

1. **ALWAYS call `finish`**: Every task MUST end with the `finish` tool. No exceptions.
2. **Complete ALL steps**: For multi-step tasks (like "search AND save"), complete EVERY step before finishing.
3. **If asked to save/write to a file**: You MUST use the `write` tool. Do not skip this step.
4. **Verify completion**: Before calling `finish`, mentally verify ALL parts of the request are done.
5. **Use markdown**: Format your final answer with markdown when appropriate.
6. **Handle failures**: If a tool fails, try an alternative approach.

# EXAMPLES OF MULTI-STEP TASKS

- "Search X and save to file Y" → web_search → write → finish
- "Read file X and analyze" → read → think → finish  
- "Calculate X and save result" → calculate → write → finish

Now, help the user with their request."""

WORKFLOW_SIMPLE = """For this SIMPLE task:
1. Identify what tool(s) are needed
2. Execute the tool(s) in order
3. IMPORTANT: If task has multiple parts (like "do X AND Y"), complete ALL parts
4. Call `finish` with your complete answer

Example: "Calculate X and tell me" → calculate → finish"""

WORKFLOW_MODERATE = """For this MODERATE task:
1. Use `think` to break down the task into steps
2. Execute each step using the appropriate tools
3. IMPORTANT: Complete ALL parts of the request before finishing
4. If asked to save/write something, you MUST use the `write` tool
5. Use `reflect` if results seem incomplete
6. Call `finish` with your complete answer

Example: "Search X and save to file Y" → think → web_search → write → finish"""

WORKFLOW_COMPLEX = """For this COMPLEX task:
1. Use `plan` to create a structured approach with ALL required steps
2. Use `think` before each major step
3. Execute tools according to your plan - DO NOT skip any step
4. Use `reflect` to verify progress after each major action
5. CHECKPOINT: Before finishing, verify ALL parts of the original request are done
6. If any part is missing, execute the required tools
7. Call `finish` with your comprehensive answer

Example: "Research X, analyze Y, and create report Z" → plan → web_search → think → write → reflect → finish"""


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
                    tool_name = tool_call.function.get("name", "")
                    
                    # Validar nombre de tool (filtrar artifacts de modelos)
                    if not is_valid_tool_name(tool_name):
                        logger.warning(
                            f"⚠️ Ignorando tool inválida: {tool_name}",
                            tool_name=tool_name
                        )
                        continue
                    
                    tool_args_str = tool_call.function.get("arguments", "{}")
                    
                    # Parsear argumentos
                    try:
                        tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                    except json.JSONDecodeError:
                        tool_args = {}
                    
                    logger.info(f"🔧 Executing tool: {tool_name}", args=list(tool_args.keys()))
                    
                    # Determinar nombre amigable para la GUI
                    tool_display_names = {
                        "think": "💭 Pensando",
                        "reflect": "🔍 Reflexionando", 
                        "plan": "📋 Planificando",
                        "read": "📖 Leyendo archivo",
                        "write": "✍️ Escribiendo archivo",
                        "edit": "✏️ Editando archivo",
                        "list": "📁 Listando directorio",
                        "search": "🔎 Buscando en archivos",
                        "shell": "💻 Ejecutando comando",
                        "python": "🐍 Ejecutando Python",
                        "javascript": "📜 Ejecutando JavaScript",
                        "web_search": "🌐 Buscando en web",
                        "web_fetch": "📥 Obteniendo URL",
                        "calculate": "🔢 Calculando",
                        "finish": "✅ Finalizando"
                    }
                    display_name = tool_display_names.get(tool_name, f"🔧 {tool_name}")
                    
                    # Yield evento de tool call (node_start para la GUI)
                    yield StreamEvent(
                        event_type="node_start",
                        execution_id=execution_id,
                        node_id=f"tool_{tool_name}_{iteration}",
                        node_name=display_name,
                        data={"tool": tool_name, "arguments": tool_args}
                    )
                    
                    # Ejecutar tool
                    result = await tool_registry.execute(tool_name, **tool_args)
                    
                    # Verificar si es finish
                    if tool_name == "finish":
                        final_answer = result.get("final_answer", "")
                        
                        yield StreamEvent(
                            event_type="node_end",
                            execution_id=execution_id,
                            node_id=f"tool_{tool_name}_{iteration}",
                            data={"tool": tool_name, "done": True, "thinking": final_answer}
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
                    
                    # Extraer contenido para herramientas de razonamiento
                    thinking_content = None
                    if tool_name in ("think", "reflect", "plan"):
                        # Estas herramientas devuelven contenido de pensamiento
                        thinking_content = result.get("thinking") or result.get("reflection") or result.get("plan") or result.get("result", "")
                    
                    # Crear preview del resultado
                    if thinking_content:
                        preview = thinking_content[:500] + "..." if len(thinking_content) > 500 else thinking_content
                    else:
                        preview = str(result)[:200]
                    
                    yield StreamEvent(
                        event_type="node_end",
                        execution_id=execution_id,
                        node_id=f"tool_{tool_name}_{iteration}",
                        data={
                            "tool": tool_name,
                            "success": result.get("success", True),
                            "thinking": thinking_content,  # Para herramientas de razonamiento
                            "observation": preview if not thinking_content else None,  # Para otras herramientas
                            "result_preview": preview
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
        # Intentar forzar una respuesta final del LLM
        logger.info("⚠️ No finish called, forcing final response")
        
        # Construir resumen de lo que se hizo
        tools_summary = ", ".join([tr["tool"] for tr in tool_results]) if tool_results else "ninguna"
        
        # Pedir al LLM que genere una respuesta final
        force_finish_prompt = f"""You have completed {iteration} iterations using these tools: {tools_summary}.

Now you MUST provide your final answer using the `finish` tool. Summarize what was accomplished and provide the answer to the user's original request.

IMPORTANT: You MUST call the `finish` tool now with your complete answer."""
        
        messages.append({"role": "user", "content": force_finish_prompt})
        
        try:
            # Una última llamada para obtener finish
            final_response = await call_llm_with_tools(
                llm_url=llm_url,
                model=model,
                messages=messages,
                tools=tools,
                temperature=0.3,  # Más determinístico para finish
                provider_type=provider_type,
                api_key=api_key
            )
            
            # Procesar respuesta
            if final_response.tool_calls:
                for tc in final_response.tool_calls:
                    if tc.function.get("name") == "finish":
                        try:
                            args = json.loads(tc.function.get("arguments", "{}"))
                            final_answer = args.get("answer", args.get("final_answer", ""))
                        except:
                            final_answer = tc.function.get("arguments", "")
                        break
            
            if not final_answer and final_response.content:
                final_answer = final_response.content
                
        except Exception as e:
            logger.error(f"Error forcing finish: {e}")
        
        # Si aún no hay respuesta, usar los resultados de las herramientas
        if not final_answer:
            if tool_results:
                # Intentar extraer información útil de los resultados
                last_results = tool_results[-3:]  # Últimos 3 resultados
                summary_parts = []
                for tr in last_results:
                    result = tr.get("result", {})
                    if isinstance(result, dict):
                        if "content" in result:
                            summary_parts.append(str(result["content"])[:500])
                        elif "data" in result:
                            summary_parts.append(str(result["data"])[:500])
                
                if summary_parts:
                    final_answer = "Resultados obtenidos:\n\n" + "\n\n".join(summary_parts)
                else:
                    final_answer = f"Tarea procesada usando: {tools_summary}. Consulta los archivos generados para ver los resultados."
            else:
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
