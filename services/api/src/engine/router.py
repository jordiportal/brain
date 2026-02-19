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


class ChainLLMConfigRequest(BaseModel):
    """Request para actualizar configuración de LLM de una cadena"""
    provider_id: Optional[int] = None
    model: Optional[str] = None


class ChainPromptUpdateRequest(BaseModel):
    """Request para actualizar el system prompt de una cadena"""
    system_prompt: str


@router.put("/{chain_id}/llm-config")
async def update_chain_llm_config(chain_id: str, request: ChainLLMConfigRequest):
    """Actualizar configuración de LLM por defecto de una cadena"""
    chain = chain_registry.get(chain_id)
    if not chain:
        raise HTTPException(status_code=404, detail=f"Cadena no encontrada: {chain_id}")
    
    from ..db.repositories.chains import ChainRepository
    
    success = await ChainRepository.update_llm_config(
        slug=chain_id,
        provider_id=request.provider_id,
        model=request.model
    )
    
    if success:
        return {
            "status": "ok",
            "message": f"Configuración de LLM actualizada para {chain_id}",
            "provider_id": request.provider_id,
            "model": request.model
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Error actualizando configuración de LLM"
        )


@router.put("/{chain_id}/prompt")
async def update_chain_prompt(chain_id: str, request: ChainPromptUpdateRequest):
    """Actualizar el system prompt de una cadena (fichero para adaptive/team, BD para otras)"""
    chain = chain_registry.get(chain_id)
    if not chain:
        raise HTTPException(status_code=404, detail=f"Cadena no encontrada: {chain_id}")

    if chain_id in ("adaptive", "team"):
        from .prompt_files import write_prompt
        success = write_prompt(chain_id, request.system_prompt)
    else:
        from ..db.repositories.chains import ChainRepository
        success = await ChainRepository.update_system_prompt(
            slug=chain_id,
            system_prompt=request.system_prompt
        )

    if success:
        return {
            "status": "ok",
            "message": f"System prompt actualizado para {chain_id}"
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Error actualizando system prompt"
        )


@router.get("/{chain_id}/details")
async def get_chain_details(chain_id: str):
    """
    Obtener detalles completos de una cadena incluyendo:
    - Configuración y prompts
    - Tools disponibles
    - Subagentes disponibles
    """
    chain = chain_registry.get(chain_id)
    if not chain:
        raise HTTPException(status_code=404, detail=f"Cadena no encontrada: {chain_id}")
    
    # Obtener tools disponibles (solo CORE, no DOMAIN ni otras)
    from ..tools import tool_registry as tr
    from ..tools.tool_registry import ToolType
    tr.register_core_tools()
    all_tools = tr.list()
    tools_info = [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "type": t.type.value if hasattr(t.type, 'value') else str(t.type),
            "category": getattr(t, 'category', 'general')
        }
        for t in all_tools
        if t.type == ToolType.CORE or t.type == ToolType.BUILTIN
    ]
    
    # Obtener subagentes disponibles
    from .chains.agents import subagent_registry, register_all_subagents
    
    subagents_info = []
    try:
        if not subagent_registry.is_initialized():
            await register_all_subagents()
        
        # Mapeo de iconos por agente
        agent_icons = {
            "designer_agent": "image",
            "researcher_agent": "search",
            "communication_agent": "campaign",
            "rag_agent": "menu_book",
            "sap_agent": "storage",
            "sap_analyst": "analytics",
            "mail_agent": "email",
            "office_agent": "description"
        }
        
        for agent in subagent_registry.list():
            subagents_info.append({
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "version": agent.version,
                "domain_tools": agent.domain_tools,
                "status": "active",
                "icon": agent_icons.get(agent.id, "smart_toy")
            })
    except Exception:
        # Si falla, continuar sin subagentes
        pass
    
    # Obtener proveedor LLM y prompt persistido desde BD (antes de extraer de nodos)
    llm_provider = None
    db_chain = None
    try:
        from ..db.repositories.chains import ChainRepository
        db_chain = await ChainRepository.get_by_slug(chain_id)
        if db_chain and db_chain.llm_provider:
            p = db_chain.llm_provider
            llm_provider = {
                "id": p.id,
                "name": p.name,
                "type": p.type,
                "baseUrl": p.base_url,
                "apiKey": p.api_key,
                "defaultModel": p.default_model,
                "isActive": p.is_active
            }
    except Exception:
        pass

    # System prompt: desde fichero (adaptive, team) o BD (otras cadenas)
    from .prompt_files import read_prompt
    if chain_id in ("adaptive", "team"):
        system_prompt = read_prompt(chain_id)
    else:
        system_prompt = ""
        if db_chain and getattr(db_chain, "prompts", None) and isinstance(db_chain.prompts, dict) and db_chain.prompts.get("system"):
            system_prompt = db_chain.prompts.get("system", "")

    return {
        "chain": {
            "id": chain.id,
            "name": chain.name,
            "description": chain.description,
            "type": chain.type,
            "version": chain.version,
            "config": chain.config.model_dump(),
            "nodes": [
                {
                    "id": n.id,
                    "name": n.name,
                    "type": n.type.value,
                    "system_prompt": n.system_prompt
                }
                for n in chain.nodes
            ],
            "edges": [
                {"source": e.source, "target": e.target, "condition": e.condition}
                for e in chain.edges
            ]
        },
        "system_prompt": system_prompt,
        "tools": tools_info,
        "subagents": subagents_info,
        "llm_provider": llm_provider
    }


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
    """Actualizar configuración de una cadena (guarda en PostgreSQL)"""
    chain = chain_registry.get(chain_id)
    if not chain:
        raise HTTPException(status_code=404, detail=f"Cadena no encontrada: {chain_id}")
    
    from ..db.repositories.chains import ChainRepository
    
    # Preparar datos para guardar
    nodes_data = update.nodes or [
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
    ]
    
    edges_data = [
        {"source": e.source, "target": e.target, "condition": e.condition}
        for e in chain.edges
    ]
    
    config_data = update.config or chain.config.model_dump()
    
    # Guardar en PostgreSQL usando upsert
    saved = await ChainRepository.upsert(
        slug=chain_id,
        name=update.name or chain.name,
        chain_type=chain.type,
        description=update.description or chain.description,
        version=chain.version,
        nodes=nodes_data,
        edges=edges_data,
        config=config_data
    )
    
    if saved:
        return {
            "status": "ok",
            "message": f"Cadena {chain_id} actualizada",
            "chain": {
                "id": chain_id,
                "name": update.name or chain.name,
                "type": chain.type,
                "description": update.description or chain.description,
                "nodes": nodes_data,
                "edges": edges_data,
                "config": config_data
            }
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Error guardando cadena en la base de datos"
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
