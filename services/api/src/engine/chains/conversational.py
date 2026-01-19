"""
Cadena Conversacional - Chat con memoria
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
    ExecutionState,
    ExecutionStep,
    StreamEvent
)
from ..registry import chain_registry
from .llm_utils import call_llm, call_llm_stream


# Definición de la cadena
CONVERSATIONAL_CHAIN = ChainDefinition(
    id="conversational",
    name="Conversational Agent",
    description="Agente conversacional con memoria de chat. Mantiene el contexto de la conversación.",
    type="conversational",
    version="1.0.0",
    nodes=[
        NodeDefinition(
            id="input",
            type=NodeType.INPUT,
            name="Entrada del usuario"
        ),
        NodeDefinition(
            id="llm",
            type=NodeType.LLM,
            name="LLM Response",
            system_prompt="Eres un asistente útil y amigable. Responde de manera clara y concisa."
        ),
        NodeDefinition(
            id="output",
            type=NodeType.OUTPUT,
            name="Respuesta"
        )
    ],
    config=ChainConfig(
        use_memory=True,
        max_memory_messages=20,
        temperature=0.7
    )
)


async def build_conversational_chain_stream(
    config: ChainConfig,
    llm_url: str,
    model: str,
    input_data: dict,
    memory: list,
    execution_id: str = "",
    provider_type: str = "ollama",
    api_key: Optional[str] = None,
    **kwargs
) -> AsyncGenerator[StreamEvent, None]:
    """Builder de la cadena conversacional con streaming"""
    
    user_message = input_data.get("message", "")
    system_prompt = config.system_prompt or CONVERSATIONAL_CHAIN.nodes[1].system_prompt
    
    # Construir mensajes
    messages = []
    
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    # Añadir memoria
    for msg in memory:
        messages.append(msg)
    
    # Añadir mensaje actual
    messages.append({"role": "user", "content": user_message})
    
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="llm",
        node_name="LLM Response",
        data={"model": model}
    )
    
    full_content = ""
    
    async for token in call_llm_stream(
        llm_url, model, messages, 
        temperature=config.temperature,
        provider_type=provider_type,
        api_key=api_key
    ):
        full_content += token
        yield StreamEvent(
            event_type="token",
            execution_id=execution_id,
            node_id="llm",
            content=token
        )
    
    yield StreamEvent(
        event_type="node_end",
        execution_id=execution_id,
        node_id="llm",
        node_name="LLM Response",
        data={"response": full_content}
    )


async def build_conversational_chain(
    config: ChainConfig,
    llm_url: str,
    model: str,
    input_data: dict,
    memory: list,
    execution_id: str = "",
    execution_state: Optional[ExecutionState] = None,
    stream: bool = False,
    provider_type: str = "ollama",
    api_key: Optional[str] = None,
    **kwargs
):
    """Builder de la cadena conversacional"""
    
    if stream:
        # Retornar el generador de streaming
        async for event in build_conversational_chain_stream(
            config=config,
            llm_url=llm_url,
            model=model,
            input_data=input_data,
            memory=memory,
            execution_id=execution_id,
            provider_type=provider_type,
            api_key=api_key
        ):
            yield event
        return
    
    # Sin streaming
    user_message = input_data.get("message", "")
    system_prompt = config.system_prompt or CONVERSATIONAL_CHAIN.nodes[1].system_prompt
    
    # Construir mensajes
    messages = []
    
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    # Añadir memoria
    for msg in memory:
        messages.append(msg)
    
    # Añadir mensaje actual
    messages.append({"role": "user", "content": user_message})
    
    start_time = datetime.utcnow()
    
    content = await call_llm(
        llm_url, model, messages,
        temperature=config.temperature,
        provider_type=provider_type,
        api_key=api_key
    )
    
    end_time = datetime.utcnow()
    
    if execution_state:
        execution_state.steps.append(ExecutionStep(
            step_number=1,
            node_id="llm",
            node_name="LLM Response",
            node_type=NodeType.LLM,
            started_at=start_time,
            completed_at=end_time,
            duration_ms=int((end_time - start_time).total_seconds() * 1000),
            input_data={"messages": messages},
            output_data={"response": content}
        ))
    
    # Para funciones no-streaming que retornan dict, usamos yield con resultado especial
    yield {"_result": {"response": content}}


def register_conversational_chain():
    """Registrar la cadena conversacional"""
    chain_registry.register(
        chain_id="conversational",
        definition=CONVERSATIONAL_CHAIN,
        builder=build_conversational_chain
    )
