"""
Brain Team - Cadena con consenso dirigido por LLM.

El coordinador usa AdaptiveExecutor con herramientas de cognición (think, reflect, plan)
y consult_team_member para pedir opiniones a los expertos; el consenso lo construye el LLM.
"""

import time
from typing import Optional, AsyncGenerator

import structlog

from ...models import StreamEvent, ChainConfig
from ...reasoning import detect_complexity, get_reasoning_config
from ....tools import tool_registry
from ..agents import register_all_subagents
from ..agents.base import subagent_registry
from ..adaptive.executor import AdaptiveExecutor
from ..adaptive.events import StreamEmitter

logger = structlog.get_logger()


async def build_team_coordinator(
    config: ChainConfig,
    llm_url: str,
    model: str,
    input_data: dict,
    memory: list,
    execution_id: str = "",
    stream: bool = True,
    provider_type: str = "ollama",
    api_key: Optional[str] = None,
    emit_brain_events: bool = True,
    **kwargs
) -> AsyncGenerator[StreamEvent, None]:
    """
    Builder del Team Coordinator - consenso dirigido por LLM.

    Usa AdaptiveExecutor con herramientas de cognición (think, reflect, plan),
    get_agent_info y consult_team_member. El LLM coordinador decide a quién consultar
    y cuándo dar la respuesta final con finish.
    """
    start_time = time.time()
    query = input_data.get("message", input_data.get("query", ""))

    # Asegurar subagentes y tools registradas
    if not subagent_registry.is_initialized():
        register_all_subagents()
    tool_registry.register_core_tools()
    tools = tool_registry.get_tools_for_team()

    logger.info(
        "👥 Brain Team starting (LLM-driven consensus)",
        query=query[:100],
        model=model,
        tools_count=len(tools)
    )

    stream_emitter = StreamEmitter(execution_id)

    yield stream_emitter.node_start(
        "team_coordinator",
        "Coordinador de equipo",
        {"query": query[:100]}
    )

    complexity = detect_complexity(query)
    reasoning_config = get_reasoning_config(complexity.level)

    # System prompt: desde fichero (prompts/system_prompt.txt)
    from ...prompt_files import read_prompt
    system_prompt = read_prompt("team")

    # Mensajes: system prompt coordinador + memoria + query
    messages = [{"role": "system", "content": system_prompt}]
    if memory and getattr(config, "use_memory", True):
        max_memory = getattr(config, "max_memory_messages", 10) or 10
        for msg in memory[-max_memory:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
    messages.append({"role": "user", "content": query})

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
        is_continue_request=False
    )

    async for event in executor.execute(messages, tools):
        yield event

    yield stream_emitter.node_end("team_coordinator", {"iterations": executor.iteration})

    # Si no hubo finish, forzar respuesta
    if executor.final_answer is None:
        async for event in executor.force_finish(messages, tools):
            yield event

    if executor.final_answer is None:
        executor.final_answer = "No se pudo completar la coordinación del equipo. Por favor, reformula la petición."

    elapsed = time.time() - start_time

    yield stream_emitter.response_complete(
        executor.final_answer,
        complexity.level.value,
        executor.iteration,
        [tr["tool"] for tr in executor.tool_results]
    )

    yield {
        "_result": {
            "response": executor.final_answer,
            "iterations": executor.iteration,
            "tools_used": [tr["tool"] for tr in executor.tool_results],
            "elapsed_ms": int(elapsed * 1000)
        }
    }
