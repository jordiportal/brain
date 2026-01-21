"""
RAG Chain - Retrieval Augmented Generation (REFACTORIZADO con estándar)
"""

import json
from typing import AsyncGenerator, Optional, List, Dict
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
from src.rag.searcher import RAGSearcher
from src.providers import get_active_llm_provider
from .llm_utils import call_llm, call_llm_stream
from .agent_helpers import build_llm_messages  # ✅ Usar helper compartido


# ============================================
# Funciones RAG específicas
# ============================================

async def search_documents(
    query: str,
    collection: str,
    top_k: int,
    embedding_base_url: str = None,
    embedding_model: str = None
) -> List[Dict]:
    """
    Buscar documentos similares en pgvector usando RAGSearcher.
    Esta función es específica del dominio RAG, no va en helpers.
    """
    try:
        # Obtener configuración de Strapi si no se proporciona
        if not embedding_base_url or not embedding_model:
            provider = await get_active_llm_provider()
            if provider:
                embedding_base_url = embedding_base_url or provider.base_url
                embedding_model = embedding_model or provider.embedding_model
        
        # Fallback - usar variable de entorno o IP directa
        import os
        embedding_base_url = embedding_base_url or os.getenv("OLLAMA_BASE_URL", "http://192.168.7.101:11434")
        embedding_model = embedding_model or "qwen3-embedding:8b"
        
        searcher = RAGSearcher(
            collection=collection,
            embedding_base_url=embedding_base_url,
            embedding_model=embedding_model
        )
        
        results = await searcher.search(
            query=query,
            top_k=top_k,
            min_score=0.3
        )
        
        return [
            {
                "content": r["content"],
                "metadata": r["metadata"],
                "score": r["score"]
            }
            for r in results
        ]
    except Exception as e:
        import structlog
        logger = structlog.get_logger()
        logger.warning(f"Error en búsqueda RAG: {e}")
        return []


def extract_source_from_metadata(metadata) -> str:
    """Helper para extraer source de metadata (puede ser dict o JSON string)"""
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except:
            return 'desconocida'
    
    if isinstance(metadata, dict):
        return metadata.get('source', 'desconocida')
    
    return 'desconocida'


def build_context_from_documents(documents: List[Dict]) -> str:
    """Construir texto de contexto a partir de documentos recuperados"""
    context_parts = []
    for doc in documents:
        source = extract_source_from_metadata(doc.get('metadata', {}))
        content = doc.get('content', '')
        context_parts.append(f"[Fuente: {source}]\n{content}")
    
    return "\n\n".join(context_parts)


# ============================================
# Definición del Agente (con prompts editables)
# ============================================

RAG_CHAIN_DEFINITION = ChainDefinition(
    id="rag",
    name="RAG Chain",
    description="Cadena de Retrieval Augmented Generation. Busca en documentos y genera respuestas basadas en el contexto.",
    type="rag",
    version="2.0.0",  # ✅ Versión actualizada
    nodes=[
        NodeDefinition(
            id="input",
            type=NodeType.INPUT,
            name="Query del usuario"
        ),
        NodeDefinition(
            id="retrieval",
            type=NodeType.RAG,
            name="Búsqueda en documentos",
            collection="default",
            top_k=5
        ),
        NodeDefinition(
            id="llm",
            type=NodeType.LLM,
            name="Generación de respuesta",
            # ✅ System prompt editable
            system_prompt="""Eres un asistente que responde preguntas basándose en el contexto proporcionado.

INSTRUCCIONES:
- Usa SOLO la información del contexto para responder
- Si el contexto no contiene información relevante, indícalo claramente
- Cita las fuentes cuando sea posible
- Sé preciso y conciso""",
            # ✅ Template con variables
            prompt_template="""CONTEXTO:
{{context}}

PREGUNTA: {{user_query}}""",
            temperature=0.3
        ),
        NodeDefinition(
            id="output",
            type=NodeType.OUTPUT,
            name="Respuesta con fuentes"
        )
    ],
    config=ChainConfig(
        use_memory=False,
        rag_collection="default",
        rag_top_k=5,
        temperature=0.3
    )
)


# ============================================
# Builder Function (Lógica del Agente)
# ============================================

async def build_rag_chain(
    config: ChainConfig,
    llm_url: str,
    model: str,
    input_data: dict,
    memory: list,
    execution_id: str = "",
    execution_state: Optional[ExecutionState] = None,
    stream: bool = True,
    provider_type: str = "ollama",
    api_key: Optional[str] = None,
    **kwargs
) -> AsyncGenerator[StreamEvent, None]:
    """
    Builder de la RAG Chain.
    
    FASES:
    1. Retrieval: Buscar documentos similares en vectorstore
    2. Generation: Generar respuesta basada en contexto
    
    NODOS:
    - input (INPUT): Query del usuario
    - retrieval (RAG): Búsqueda semántica en documentos
    - llm (LLM): Generación de respuesta con contexto
    - output (OUTPUT): Respuesta con fuentes
    
    MEMORY: No (cada consulta es independiente)
    TOOLS: None (usa RAG vectorstore)
    """
    
    query = input_data.get("query", input_data.get("message", ""))
    collection = config.rag_collection or "default"
    top_k = config.rag_top_k or 5
    
    # ✅ Obtener nodo LLM con prompt editable
    llm_node = RAG_CHAIN_DEFINITION.get_node("llm")
    if not llm_node:
        raise ValueError("Nodo LLM no encontrado en RAG Chain")
    
    # ========== FASE 1: RETRIEVAL ==========
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="retrieval",
        node_name="Búsqueda en documentos",
        data={"query": query, "collection": collection, "top_k": top_k}
    )
    
    documents = await search_documents(
        query, collection, top_k,
        embedding_base_url=llm_url
    )
    
    yield StreamEvent(
        event_type="node_end",
        execution_id=execution_id,
        node_id="retrieval",
        node_name="Búsqueda en documentos",
        data={"documents_found": len(documents)}
    )
    
    # ========== FASE 2: GENERATION ==========
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="llm",
        node_name="Generación de respuesta",
        data={"model": model}
    )
    
    # Construir contexto de documentos
    context = build_context_from_documents(documents)
    
    # ✅ Construir mensajes con helper estándar
    system_prompt = config.system_prompt or llm_node.system_prompt
    messages = build_llm_messages(
        system_prompt=system_prompt,
        template=llm_node.prompt_template,
        variables={
            "context": context,
            "user_query": query
        },
        memory=None,  # RAG no usa memoria conversacional
        max_memory=0
    )
    
    # Streaming de respuesta
    full_content = ""
    async for token in call_llm_stream(
        llm_url, model, messages,
        temperature=llm_node.temperature,
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
    
    sources = [extract_source_from_metadata(d.get('metadata', {})) for d in documents]
    
    yield StreamEvent(
        event_type="node_end",
        execution_id=execution_id,
        node_id="llm",
        node_name="Generación de respuesta",
        data={"sources": sources}
    )
    
    # Para modo no-streaming
    if not stream:
        yield {"_result": {
            "response": full_content,
            "sources": sources,
            "documents_found": len(documents)
        }}


# ============================================
# Registro del Agente
# ============================================

def register_rag_chain():
    """Registrar la RAG Chain en el registry"""
    
    chain_registry.register(
        chain_id="rag",
        definition=RAG_CHAIN_DEFINITION,
        builder=build_rag_chain
    )
