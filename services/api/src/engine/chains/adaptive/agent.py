"""
Brain 2.0 Adaptive Agent - Builder Principal

Este archivo contiene el builder principal (build_adaptive_agent).
La definición (prompt, tools, config) se carga de BD al iniciar.
El flujo de ejecución se delega al AdaptiveExecutor.
"""

from typing import AsyncGenerator, Optional

import structlog

from ...models import (
    ChainConfig,
    StreamEvent
)
from ...reasoning import detect_complexity, get_reasoning_config
from ....tools import tool_registry

from .validators import is_continue_command
from .executor import AdaptiveExecutor
from .events import StreamEmitter, BrainEmitter
from ...context_injector import apply_user_context


logger = structlog.get_logger()


# ============================================
# Builder Principal
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
    emit_brain_events: bool = False,
    user_id: Optional[str] = None,
    **kwargs
) -> AsyncGenerator[StreamEvent, None]:
    """
    Builder del Adaptive Agent de Brain 2.0.
    
    Flujo:
    1. Detectar complejidad de la query
    2. Configurar modo de razonamiento
    3. Delegar al AdaptiveExecutor
    
    Args:
        config: Configuración de la cadena
        llm_url: URL del proveedor LLM
        model: Nombre del modelo
        input_data: Input con 'message' o 'query'
        memory: Historial de mensajes
        execution_id: ID de ejecución
        stream: Si es streaming
        provider_type: Tipo de proveedor (ollama, openai, anthropic, etc.)
        api_key: API key si es necesaria
        emit_brain_events: Si True, emite Brain Events para Open WebUI
        
    Yields:
        StreamEvents durante la ejecución
    """
    query = input_data.get("message", input_data.get("query", ""))
    is_continue_request = is_continue_command(query)
    
    logger.info(
        "🧠 Brain 2.0 Adaptive Agent starting",
        query=query[:100],
        model=model,
        provider=provider_type,
        is_continue=is_continue_request,
        user_id=user_id,
    )
    
    # ========== FASE 1: ANÁLISIS DE COMPLEJIDAD ==========
    
    stream_emitter = StreamEmitter(execution_id)
    brain_emitter = BrainEmitter(execution_id, enabled=emit_brain_events)
    
    yield stream_emitter.node_start(
        "complexity_analysis",
        "Analyzing task complexity",
        {"query": query[:100]}
    )
    
    complexity = detect_complexity(query)
    reasoning_config = get_reasoning_config(complexity.level)
    
    yield stream_emitter.node_end(
        "complexity_analysis",
        {
            "is_trivial": complexity.is_trivial,
            "reasoning_mode": reasoning_config.mode.value
        }
    )
    
    # Brain Event de thinking inicial (solo si no es trivial)
    if not complexity.is_trivial:
        thinking_event = brain_emitter.thinking_start(
            f"Analizando solicitud...\n\n"
            f"El LLM decidirá qué herramientas usar"
        )
        if thinking_event:
            yield thinking_event
    
    # ========== FASE 2: PREPARAR MENSAJES Y TOOLS ==========
    
    system_prompt = config.system_prompt or ""
    if not system_prompt:
        logger.warning("⚠️ No system prompt in config, using empty")

    tool_registry.register_core_tools()
    tools = tool_registry.get_tools_for_llm(tool_registry.ADAPTIVE_TOOL_IDS)

    logger.info(f"📦 {len(tools)} core tools loaded")
    logger.info(f"📝 System prompt: {len(system_prompt)} chars")
    
    # Inyectar contexto del usuario (briefing + personal_prompt)
    briefing_messages: list[dict] = []
    system_prompt = await apply_user_context(user_id, briefing_messages, system_prompt)

    # Construir mensajes
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(briefing_messages)

    # Agregar memoria
    if memory and config.use_memory:
        max_memory = config.max_memory_messages or 10
        for msg in memory[-max_memory:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
    
    # Agregar query actual
    messages.append({"role": "user", "content": query})
    
    # ========== FASE 3: EJECUTAR ==========
    
    # Crear executor
    executor = AdaptiveExecutor(
        execution_id=execution_id,
        llm_url=llm_url,
        model=model,
        provider_type=provider_type,
        api_key=api_key,
        complexity=complexity,
        reasoning_config=reasoning_config,
        chain_config=config,
        emit_brain_events=emit_brain_events,
        is_continue_request=is_continue_request
    )
    
    # Si es comando de continuar, emitir evento
    if is_continue_request:
        logger.info(f"🔄 Continue request, max_iterations: {executor.max_iterations}")
        yield stream_emitter.node_start(
            "continue_execution",
            "Continuando ejecución",
            {"extended_iterations": executor.max_iterations}
        )
    
    # Ejecutar loop principal
    async for event in executor.execute(messages, tools):
        yield event
    
    # ========== FASE 4: FINALIZACIÓN ==========
    
    # Verificar si llegamos al límite sin finalizar
    if executor.final_answer is None and executor.iteration >= executor.max_iterations:
        logger.info(f"⚠️ Iteration limit reached ({executor.max_iterations})")
        
        if executor.ask_before_continue:
            # Emitir mensaje de límite
            limit_message = executor.get_iteration_limit_message()
            
            yield stream_emitter.iteration_limit(
                executor.iteration,
                executor.max_iterations,
                [tr["tool"] for tr in executor.tool_results],
                limit_message
            )
            
            yield stream_emitter.token(limit_message)
            
            yield stream_emitter.response_complete(
                limit_message,
                complexity.level.value,
                executor.iteration,
                [tr["tool"] for tr in executor.tool_results],
                iteration_limit_reached=True,
                can_continue=True
            )
            
            yield {
                "_result": {
                    "response": limit_message,
                    "complexity": complexity.level.value,
                    "reasoning_mode": reasoning_config.mode.value,
                    "iterations": executor.iteration,
                    "tools_used": [tr["tool"] for tr in executor.tool_results],
                    "iteration_limit_reached": True,
                    "images": executor.images,  # Imágenes generadas durante ejecución
                    "videos": executor.videos   # Vídeos generados durante ejecución
                }
            }
            return
    
    # Si no hay respuesta final, forzar una
    if executor.final_answer is None:
        logger.info("⚠️ No finish called, forcing final response")
        async for event in executor.force_finish(messages, tools):
            yield event
    
    # Eventos de completado
    yield stream_emitter.response_complete(
        executor.final_answer,
        complexity.level.value,
        executor.iteration,
        [tr["tool"] for tr in executor.tool_results]
    )
    
    yield {
        "_result": {
            "response": executor.final_answer,
            "complexity": complexity.level.value,
            "reasoning_mode": reasoning_config.mode.value,
            "iterations": executor.iteration,
            "tools_used": [tr["tool"] for tr in executor.tool_results],
            "images": executor.images,  # Imágenes generadas durante ejecución
            "videos": executor.videos   # Vídeos generados durante ejecución
        }
    }
