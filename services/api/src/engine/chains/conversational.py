"""
Cadena Conversacional - Chat con memoria
"""

import json
from typing import AsyncGenerator, Optional
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
    tokens = 0
    
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
                            full_content += content
                            yield StreamEvent(
                                event_type="token",
                                execution_id=execution_id,
                                node_id="llm",
                                content=content
                            )
                        if data.get("done"):
                            tokens = data.get("eval_count", 0)
                    except json.JSONDecodeError:
                        continue
    
    yield StreamEvent(
        event_type="node_end",
        execution_id=execution_id,
        node_id="llm",
        node_name="LLM Response",
        data={"tokens": tokens, "response": full_content}
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
            execution_id=execution_id
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
        content = data.get("message", {}).get("content", "")
        tokens = data.get("eval_count", 0)
    
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
            output_data={"response": content},
            tokens_used=tokens
        ))
        execution_state.total_tokens = tokens
    
    # Para funciones no-streaming que retornan dict, usamos yield con resultado especial
    yield {"_result": {"response": content, "tokens": tokens}}


def register_conversational_chain():
    """Registrar la cadena conversacional"""
    chain_registry.register(
        chain_id="conversational",
        definition=CONVERSATIONAL_CHAIN,
        builder=build_conversational_chain
    )
