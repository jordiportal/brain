"""
Conversational Agent - Chat con memoria (REFACTORIZADO con estándar)
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
from .agent_helpers import build_llm_messages  # ✅ Usar helper compartido


# ============================================
# Definición del Agente (con prompts editables)
# ============================================

CONVERSATIONAL_DEFINITION = ChainDefinition(
    id="conversational",
    name="Conversational Agent",
    description="Agente conversacional con memoria de chat. Mantiene el contexto de la conversación.",
    type="conversational",
    version="2.0.0",  # ✅ Versión actualizada
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
            # ✅ System prompt editable desde Strapi
            system_prompt="Eres un asistente útil y amigable. Responde de manera clara y concisa.",
            # ✅ Template con variable (aunque en este caso es simple)
            prompt_template="{{user_message}}"
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


# ============================================
# Builder Function (Lógica del Agente)
# ============================================

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
    """
    Builder de la cadena conversacional con streaming.
    
    FASES:
    1. LLM: Generar respuesta conversacional con memoria
    
    NODOS:
    - input (INPUT): Mensaje del usuario
    - llm (LLM): Generación de respuesta
    - output (OUTPUT): Respuesta final
    
    MEMORY: Yes (hasta 20 mensajes)
    TOOLS: None
    """
    
    user_message = input_data.get("message", "")
    
    # ✅ Obtener nodo LLM con prompts editables
    llm_node = CONVERSATIONAL_DEFINITION.get_node("llm")
    if not llm_node:
        raise ValueError("Nodo LLM no encontrado en la definición")
    
    # Permitir override del system prompt desde config
    system_prompt = config.system_prompt or llm_node.system_prompt
    
    # ✅ Construir mensajes usando helper estándar
    messages = build_llm_messages(
        system_prompt=system_prompt,
        template=llm_node.prompt_template,
        variables={"user_message": user_message},
        memory=memory,
        max_memory=config.max_memory_messages
    )
    
    # ========== FASE: LLM Response ==========
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="llm",
        node_name="LLM Response",
        data={"model": model, "provider": provider_type}
    )
    
    full_content = ""
    
    # Streaming de respuesta
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
    provider_type: str = "ollama",
    api_key: Optional[str] = None,
    **kwargs
):
    """Builder sin streaming (modo no-streaming)"""
    
    user_message = input_data.get("message", "")
    
    # ✅ Obtener nodo LLM
    llm_node = CONVERSATIONAL_DEFINITION.get_node("llm")
    if not llm_node:
        raise ValueError("Nodo LLM no encontrado")
    
    system_prompt = config.system_prompt or llm_node.system_prompt
    
    # ✅ Construir mensajes con helper
    messages = build_llm_messages(
        system_prompt=system_prompt,
        template=llm_node.prompt_template,
        variables={"user_message": user_message},
        memory=memory,
        max_memory=config.max_memory_messages
    )
    
    # Llamada directa al LLM
    response = await call_llm(
        llm_url, model, messages,
        temperature=config.temperature,
        provider_type=provider_type,
        api_key=api_key
    )
    
    # Resultado final
    yield {
        "_result": {
            "response": response,
            "model": model,
            "provider": provider_type
        }
    }


# ============================================
# Registro del Agente
# ============================================

def register_conversational_chain():
    """Registrar el agente conversacional en el registry"""
    
    # Registrar versión streaming
    chain_registry.register(
        chain_id="conversational",
        definition=CONVERSATIONAL_DEFINITION,
        builder=build_conversational_chain_stream
    )
    
    # También registrar versión no-streaming
    chain_registry.register(
        chain_id="conversational_no_stream",
        definition=CONVERSATIONAL_DEFINITION,
        builder=build_conversational_chain
    )
