"""
RAG Chain - Retrieval Augmented Generation
"""

import json
from typing import AsyncGenerator, Optional, List, Dict
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
from src.rag.searcher import RAGSearcher
from src.providers import get_active_llm_provider


# Definición de la cadena RAG
RAG_CHAIN = ChainDefinition(
    id="rag",
    name="RAG Chain",
    description="Cadena de Retrieval Augmented Generation. Busca en documentos y genera respuestas basadas en el contexto.",
    type="rag",
    version="1.0.0",
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
            system_prompt="""Eres un asistente que responde preguntas basándose en el contexto proporcionado.
            
INSTRUCCIONES:
- Usa SOLO la información del contexto para responder
- Si el contexto no contiene información relevante, indícalo claramente
- Cita las fuentes cuando sea posible
- Sé preciso y conciso"""
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
        temperature=0.3  # Más determinista para RAG
    )
)


async def search_documents(
    query: str,
    collection: str,
    top_k: int,
    embedding_base_url: str = None,
    embedding_model: str = None
) -> List[Dict]:
    """Buscar documentos similares en pgvector usando RAGSearcher"""
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
            min_score=0.3  # Threshold más bajo para no perder resultados
        )
        
        # Convertir al formato esperado
        return [
            {
                "content": r["content"],
                "metadata": r["metadata"],
                "score": r["score"]
            }
            for r in results
        ]
    except Exception as e:
        # Si hay error (ej: tabla no existe), retornar lista vacía
        import structlog
        logger = structlog.get_logger()
        logger.warning(f"Error en búsqueda RAG: {e}")
        return []


async def build_rag_chain(
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
    """Builder de la cadena RAG"""
    
    query = input_data.get("query", input_data.get("message", ""))
    collection = config.rag_collection or "default"
    top_k = config.rag_top_k or 5
    
    if stream:
        # Paso 1: Búsqueda
        yield StreamEvent(
            event_type="node_start",
            execution_id=execution_id,
            node_id="retrieval",
            node_name="Búsqueda en documentos",
            data={"query": query, "collection": collection, "top_k": top_k}
        )
        
        # Usar la misma URL del LLM para embeddings (es el mismo servidor Ollama)
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
        
        # Construir contexto (metadata puede ser string JSON o dict)
        def get_source(doc):
            metadata = doc.get('metadata', {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            return metadata.get('source', 'desconocida') if isinstance(metadata, dict) else 'desconocida'
        
        context = "\n\n".join([
            f"[Fuente: {get_source(doc)}]\n{doc['content']}"
            for doc in documents
        ])
        
        # Paso 2: Generación
        yield StreamEvent(
            event_type="node_start",
            execution_id=execution_id,
            node_id="llm",
            node_name="Generación de respuesta",
            data={"model": model}
        )
        
        system_prompt = config.system_prompt or RAG_CHAIN.nodes[2].system_prompt
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"CONTEXTO:\n{context}\n\nPREGUNTA: {query}"}
        ]
        
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
            node_name="Generación de respuesta",
            data={
                "tokens": tokens,
                "sources": [get_source(d) for d in documents]
            }
        )
    
    else:
        # Sin streaming
        start_time = datetime.utcnow()
        
        # Búsqueda (usar misma URL del LLM para embeddings)
        documents = await search_documents(
            query, collection, top_k,
            embedding_base_url=llm_url
        )
        
        retrieval_time = datetime.utcnow()
        
        if execution_state:
            execution_state.steps.append(ExecutionStep(
                step_number=1,
                node_id="retrieval",
                node_name="Búsqueda en documentos",
                node_type=NodeType.RAG,
                started_at=start_time,
                completed_at=retrieval_time,
                duration_ms=int((retrieval_time - start_time).total_seconds() * 1000),
                input_data={"query": query},
                output_data={"documents_found": len(documents)}
            ))
        
        # Construir contexto (metadata puede ser string JSON o dict)
        def get_source_ns(doc):
            metadata = doc.get('metadata', {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            return metadata.get('source', 'desconocida') if isinstance(metadata, dict) else 'desconocida'
        
        context = "\n\n".join([
            f"[Fuente: {get_source_ns(doc)}]\n{doc['content']}"
            for doc in documents
        ])
        
        system_prompt = config.system_prompt or RAG_CHAIN.nodes[2].system_prompt
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"CONTEXTO:\n{context}\n\nPREGUNTA: {query}"}
        ]
        
        # Generación
        llm_start = datetime.utcnow()
        
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
        
        llm_end = datetime.utcnow()
        
        if execution_state:
            execution_state.steps.append(ExecutionStep(
                step_number=2,
                node_id="llm",
                node_name="Generación de respuesta",
                node_type=NodeType.LLM,
                started_at=llm_start,
                completed_at=llm_end,
                duration_ms=int((llm_end - llm_start).total_seconds() * 1000),
                input_data={"messages": messages},
                output_data={"response": content},
                tokens_used=tokens
            ))
            execution_state.total_tokens = tokens
        
        sources = [get_source_ns(d) for d in documents]
        
        yield {"_result": {
            "response": content,
            "sources": sources,
            "documents_found": len(documents),
            "tokens": tokens
        }}


def register_rag_chain():
    """Registrar la cadena RAG"""
    chain_registry.register(
        chain_id="rag",
        definition=RAG_CHAIN,
        builder=build_rag_chain
    )
