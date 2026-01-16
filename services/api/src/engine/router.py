"""
Router de la API para cadenas y ejecuciones
"""

import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .models import (
    ChainInvokeRequest,
    ChainInvokeResponse,
    ChainDefinition,
    ChainConfig,
    ExecutionStatus,
    StreamEvent
)
from .registry import chain_registry
from .executor import chain_executor
from .persistence import chain_persistence

router = APIRouter(prefix="/chains", tags=["Chains"])


class ChainListResponse(BaseModel):
    chains: list[dict]


class ChainDetailResponse(BaseModel):
    chain: dict


@router.get("", response_model=ChainListResponse)
async def list_chains():
    """Listar todas las cadenas disponibles"""
    chains = chain_registry.list_chains()
    return ChainListResponse(
        chains=[
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "type": c.type,
                "version": c.version,
                "nodes": [{"id": n.id, "name": n.name, "type": n.type.value} for n in c.nodes],
                "config": {
                    "use_memory": c.config.use_memory,
                    "temperature": c.config.temperature
                }
            }
            for c in chains
        ]
    )


@router.get("/{chain_id}")
async def get_chain(chain_id: str):
    """Obtener detalles de una cadena"""
    chain = chain_registry.get(chain_id)
    if not chain:
        raise HTTPException(status_code=404, detail=f"Cadena no encontrada: {chain_id}")
    
    return {
        "chain": {
            "id": chain.id,
            "name": chain.name,
            "description": chain.description,
            "type": chain.type,
            "version": chain.version,
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "type": n.type.value,
                    "config": n.config,
                    "system_prompt": n.system_prompt
                }
                for n in chain.nodes
            ],
            "edges": [{"source": e.source, "target": e.target} for e in chain.edges],
            "config": chain.config.model_dump()
        }
    }


@router.post("/{chain_id}/invoke")
async def invoke_chain(
    chain_id: str,
    request: ChainInvokeRequest,
    session_id: Optional[str] = Query(None, description="ID de sesión para memoria")
):
    """Invocar una cadena (sin streaming)"""
    if not chain_registry.exists(chain_id):
        raise HTTPException(status_code=404, detail=f"Cadena no encontrada: {chain_id}")
    
    try:
        result = await chain_executor.invoke(chain_id, request, session_id)
        
        return {
            "execution_id": result.execution_id,
            "status": result.status.value,
            "output": result.output_data,
            "steps": [
                {
                    "step": s.step_number,
                    "node_id": s.node_id,
                    "node_name": s.node_name,
                    "duration_ms": s.duration_ms,
                    "tokens": s.tokens_used
                }
                for s in result.steps
            ],
            "total_tokens": result.total_tokens,
            "total_duration_ms": result.total_duration_ms,
            "error": result.error
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{chain_id}/invoke/stream")
async def invoke_chain_stream(
    chain_id: str,
    request: ChainInvokeRequest,
    session_id: Optional[str] = Query(None, description="ID de sesión para memoria")
):
    """Invocar una cadena con streaming de eventos (SSE)"""
    if not chain_registry.exists(chain_id):
        raise HTTPException(status_code=404, detail=f"Cadena no encontrada: {chain_id}")
    
    async def event_generator():
        try:
            async for event in chain_executor.invoke_stream(chain_id, request, session_id):
                event_data = {
                    "event_type": event.event_type,
                    "execution_id": event.execution_id,
                    "timestamp": event.timestamp.isoformat(),
                    "node_id": event.node_id,
                    "node_name": event.node_name,
                    "content": event.content,
                    "data": event.data
                }
                yield f"data: {json.dumps(event_data)}\n\n"
        except Exception as e:
            error_event = {
                "event_type": "error",
                "execution_id": "",
                "data": {"error": str(e)}
            }
            yield f"data: {json.dumps(error_event)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/{chain_id}/memory/{session_id}")
async def get_session_memory(chain_id: str, session_id: str):
    """Obtener memoria de una sesión"""
    memory = chain_executor.get_memory(session_id)
    return {
        "session_id": session_id,
        "messages": memory,
        "message_count": len(memory)
    }


@router.delete("/{chain_id}/memory/{session_id}")
async def clear_session_memory(chain_id: str, session_id: str):
    """Limpiar memoria de una sesión"""
    chain_executor.clear_memory(session_id)
    return {"status": "ok", "message": f"Memoria de sesión {session_id} eliminada"}


# Configuración dinámica del executor
@router.post("/config/llm")
async def configure_default_llm(
    llm_provider_url: str,
    default_model: str
):
    """Configurar LLM por defecto del executor"""
    chain_executor.llm_provider_url = llm_provider_url
    chain_executor.default_model = default_model
    return {
        "status": "ok",
        "llm_provider_url": llm_provider_url,
        "default_model": default_model
    }


# ============================================
# Endpoints de edición y persistencia
# ============================================

class NodeUpdateRequest(BaseModel):
    """Request para actualizar un nodo"""
    id: str
    name: Optional[str] = None
    system_prompt: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    collection: Optional[str] = None
    top_k: Optional[int] = None


class ChainUpdateRequest(BaseModel):
    """Request para actualizar una cadena"""
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    config: Optional[Dict[str, Any]] = None


@router.get("/{chain_id}/full")
async def get_chain_full(chain_id: str):
    """Obtener definición completa de una cadena para edición"""
    chain = chain_registry.get(chain_id)
    if not chain:
        raise HTTPException(status_code=404, detail=f"Cadena no encontrada: {chain_id}")
    
    # Obtener versión de Strapi si existe
    strapi_chain = await chain_persistence.get_chain(chain_id)
    
    # Construir respuesta con todos los detalles
    return {
        "chain": {
            "id": chain.id,
            "name": chain.name,
            "description": chain.description,
            "type": chain.type,
            "version": chain.version,
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "type": n.type.value,
                    "system_prompt": n.system_prompt,
                    "config": n.config,
                    "collection": n.collection,
                    "top_k": n.top_k,
                    "tools": n.tools
                }
                for n in chain.nodes
            ],
            "edges": [
                {"source": e.source, "target": e.target, "condition": e.condition}
                for e in chain.edges
            ],
            "config": chain.config.model_dump()
        },
        "strapi_version": {
            "exists": strapi_chain is not None,
            "documentId": strapi_chain.documentId if strapi_chain else None,
            "nodes": strapi_chain.nodes if strapi_chain else None,
            "config": strapi_chain.config if strapi_chain else None
        } if strapi_chain else None,
        "editable": True
    }


@router.put("/{chain_id}")
async def update_chain(chain_id: str, update: ChainUpdateRequest):
    """Actualizar configuración de una cadena (guarda en Strapi)"""
    chain = chain_registry.get(chain_id)
    if not chain:
        raise HTTPException(status_code=404, detail=f"Cadena no encontrada: {chain_id}")
    
    # Preparar datos para guardar
    chain_data = {
        "id": chain.id,
        "slug": chain.id,
        "name": update.name or chain.name,
        "type": chain.type,
        "description": update.description or chain.description,
        "version": chain.version,
        "nodes": update.nodes or [
            {
                "id": n.id,
                "type": n.type.value,
                "name": n.name,
                "system_prompt": n.system_prompt,
                "config": n.config,
                "collection": n.collection,
                "top_k": n.top_k,
                "tools": n.tools
            }
            for n in chain.nodes
        ],
        "edges": [
            {"source": e.source, "target": e.target, "condition": e.condition}
            for e in chain.edges
        ],
        "config": update.config or chain.config.model_dump(),
        "isActive": True
    }
    
    # Guardar en Strapi
    saved = await chain_persistence.save_chain(chain_data)
    
    if saved:
        return {
            "status": "ok",
            "message": f"Cadena {chain_id} actualizada",
            "chain": chain_data
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Error guardando cadena en Strapi. Verifica permisos."
        )


@router.put("/{chain_id}/node/{node_id}")
async def update_chain_node(chain_id: str, node_id: str, update: NodeUpdateRequest):
    """Actualizar un nodo específico de una cadena"""
    chain = chain_registry.get(chain_id)
    if not chain:
        raise HTTPException(status_code=404, detail=f"Cadena no encontrada: {chain_id}")
    
    # Buscar el nodo
    node = None
    for n in chain.nodes:
        if n.id == node_id:
            node = n
            break
    
    if not node:
        raise HTTPException(status_code=404, detail=f"Nodo no encontrado: {node_id}")
    
    # Preparar datos actualizados
    nodes_data = []
    for n in chain.nodes:
        node_data = {
            "id": n.id,
            "type": n.type.value,
            "name": n.name,
            "system_prompt": n.system_prompt,
            "config": n.config,
            "collection": n.collection,
            "top_k": n.top_k,
            "tools": n.tools
        }
        
        # Aplicar actualizaciones al nodo objetivo
        if n.id == node_id:
            if update.name is not None:
                node_data["name"] = update.name
            if update.system_prompt is not None:
                node_data["system_prompt"] = update.system_prompt
            if update.config is not None:
                node_data["config"] = update.config
            if update.collection is not None:
                node_data["collection"] = update.collection
            if update.top_k is not None:
                node_data["top_k"] = update.top_k
        
        nodes_data.append(node_data)
    
    # Guardar en Strapi
    chain_data = {
        "id": chain.id,
        "slug": chain.id,
        "name": chain.name,
        "type": chain.type,
        "description": chain.description,
        "version": chain.version,
        "nodes": nodes_data,
        "edges": [
            {"source": e.source, "target": e.target, "condition": e.condition}
            for e in chain.edges
        ],
        "config": chain.config.model_dump(),
        "isActive": True
    }
    
    saved = await chain_persistence.save_chain(chain_data)
    
    if saved:
        return {
            "status": "ok",
            "message": f"Nodo {node_id} actualizado",
            "node": next(n for n in nodes_data if n["id"] == node_id)
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Error guardando cambios en Strapi. Verifica permisos."
        )


@router.post("/sync")
async def sync_chains_to_strapi():
    """Sincronizar todas las cadenas del registry a Strapi"""
    results = await chain_persistence.sync_from_registry(chain_registry)
    
    return {
        "status": "ok",
        "message": f"Sincronizadas {len(results['synced'])} cadenas",
        "synced": results["synced"],
        "errors": results["errors"]
    }


@router.get("/strapi/list")
async def list_strapi_chains():
    """Listar cadenas guardadas en Strapi"""
    chains = await chain_persistence.list_chains()
    
    return {
        "chains": [
            {
                "id": c.id,
                "documentId": c.documentId,
                "name": c.name,
                "slug": c.slug,
                "type": c.type,
                "description": c.description,
                "version": c.version,
                "isActive": c.isActive,
                "nodes_count": len(c.nodes),
                "edges_count": len(c.edges)
            }
            for c in chains
        ],
        "total": len(chains)
    }
