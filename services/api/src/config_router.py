"""
Config Router - Endpoints para configuración del sistema
Accede directamente a PostgreSQL
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.db import get_db
from src.db.repositories import (
    LLMProviderRepository,
    ChainRepository,
    ApiKeyRepository,
    ModelConfigRepository,
    OpenAPIConnectionRepository,
    BrainSettingsRepository,
)
from src.db.repositories.mcp_connections import MCPConnectionRepository

router = APIRouter(prefix="/config", tags=["Configuration"])


# ===========================================
# Response Models
# ===========================================

class LLMProviderResponse(BaseModel):
    id: int
    documentId: Optional[str] = None
    name: str
    type: str
    baseUrl: str
    apiKey: Optional[str] = None
    defaultModel: Optional[str] = None
    embeddingModel: Optional[str] = None
    isActive: bool = True
    isDefault: bool = False  # Proveedor preferido
    config: Optional[Dict[str, Any]] = None
    description: Optional[str] = None


class MCPConnectionResponse(BaseModel):
    id: int
    documentId: Optional[str] = None
    name: str
    type: Optional[str] = None
    serverUrl: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    isActive: bool = True
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class BrainChainResponse(BaseModel):
    id: int
    documentId: Optional[str] = None
    name: str
    slug: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    isActive: bool = True
    handlerType: Optional[str] = None


class SystemStatsResponse(BaseModel):
    chains: int = 0
    llmProviders: int = 0
    mcpConnections: int = 0
    apiKeys: int = 0
    openApiConnections: int = 0


class ApiKeyResponse(BaseModel):
    id: int
    documentId: Optional[str] = None
    name: str
    key: Optional[str] = None  # Para mostrar prefix en listado
    keyPrefix: Optional[str] = None
    isActive: bool = True
    permissions: Optional[Dict[str, Any]] = None
    usageStats: Optional[Dict[str, Any]] = None
    expiresAt: Optional[str] = None
    createdByUser: Optional[str] = None
    notes: Optional[str] = None
    createdAt: Optional[str] = None


# ===========================================
# LLM Providers
# ===========================================

@router.get("/llm-providers", response_model=List[LLMProviderResponse])
async def get_llm_providers(active_only: bool = False):
    """Obtener lista de proveedores LLM"""
    try:
        providers = await LLMProviderRepository.get_all(active_only=active_only)
        return [
            LLMProviderResponse(
                id=p.id,
                documentId=p.document_id,
                name=p.name or "",
                type=p.type or "ollama",
                baseUrl=p.base_url or "",
                apiKey=p.api_key,
                defaultModel=p.default_model,
                embeddingModel=p.embedding_model,
                isActive=p.is_active,
                isDefault=p.is_default,
                config=p.config,
                description=p.description
            )
            for p in providers
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/llm-providers/{provider_id}", response_model=LLMProviderResponse)
async def get_llm_provider(provider_id: int):
    """Obtener un proveedor LLM por ID"""
    try:
        provider = await LLMProviderRepository.get_by_id(provider_id)
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        return LLMProviderResponse(
            id=provider.id,
            documentId=provider.document_id,
            name=provider.name or "",
            type=provider.type or "ollama",
            baseUrl=provider.base_url or "",
            apiKey=provider.api_key,
            defaultModel=provider.default_model,
            embeddingModel=provider.embedding_model,
            isActive=provider.is_active,
            config=provider.config,
            description=provider.description
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# LLM Provider Create/Update/Delete
# ===========================================

class LLMProviderCreateRequest(BaseModel):
    name: str
    type: str = "ollama"
    baseUrl: str
    apiKey: Optional[str] = None
    defaultModel: Optional[str] = None
    embeddingModel: Optional[str] = None
    isActive: bool = True
    isDefault: bool = False
    description: Optional[str] = None


class LLMProviderUpdateRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    baseUrl: Optional[str] = None
    apiKey: Optional[str] = None
    defaultModel: Optional[str] = None
    embeddingModel: Optional[str] = None
    isActive: Optional[bool] = None
    isDefault: Optional[bool] = None
    description: Optional[str] = None


@router.post("/llm-providers", response_model=LLMProviderResponse)
async def create_llm_provider(request: LLMProviderCreateRequest):
    """Crear nuevo proveedor LLM"""
    try:
        db = get_db()
        
        query = """
            INSERT INTO llm_providers (name, type, base_url, api_key, default_model, embedding_model, is_active, is_default, description, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
            RETURNING id
        """
        
        result = await db.fetch_one(
            query,
            request.name,
            request.type,
            request.baseUrl,
            request.apiKey,
            request.defaultModel,
            request.embeddingModel,
            request.isActive,
            request.isDefault,
            request.description
        )
        
        return LLMProviderResponse(
            id=result["id"],
            documentId=str(result["id"]),
            name=request.name,
            type=request.type,
            baseUrl=request.baseUrl,
            apiKey=request.apiKey,
            defaultModel=request.defaultModel,
            embeddingModel=request.embeddingModel,
            isActive=request.isActive,
            isDefault=request.isDefault,
            description=request.description
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/llm-providers/{provider_id}", response_model=LLMProviderResponse)
async def update_llm_provider(provider_id: int, request: LLMProviderUpdateRequest):
    """Actualizar proveedor LLM"""
    try:
        db = get_db()
        
        # Construir query dinámico solo con campos proporcionados
        updates = []
        values = []
        param_idx = 1
        
        if request.name is not None:
            updates.append(f"name = ${param_idx}")
            values.append(request.name)
            param_idx += 1
        
        if request.type is not None:
            updates.append(f"type = ${param_idx}")
            values.append(request.type)
            param_idx += 1
        
        if request.baseUrl is not None:
            updates.append(f"base_url = ${param_idx}")
            values.append(request.baseUrl)
            param_idx += 1
        
        if request.apiKey is not None:
            updates.append(f"api_key = ${param_idx}")
            values.append(request.apiKey)
            param_idx += 1
        
        if request.defaultModel is not None:
            updates.append(f"default_model = ${param_idx}")
            values.append(request.defaultModel)
            param_idx += 1
        
        if request.embeddingModel is not None:
            updates.append(f"embedding_model = ${param_idx}")
            values.append(request.embeddingModel)
            param_idx += 1
        
        if request.isActive is not None:
            updates.append(f"is_active = ${param_idx}")
            values.append(request.isActive)
            param_idx += 1
        
        if request.isDefault is not None:
            updates.append(f"is_default = ${param_idx}")
            values.append(request.isDefault)
            param_idx += 1
        
        if request.description is not None:
            updates.append(f"description = ${param_idx}")
            values.append(request.description)
            param_idx += 1
        
        if not updates:
            # No hay cambios, devolver el provider actual
            provider = await LLMProviderRepository.get_by_id(provider_id)
            if not provider:
                raise HTTPException(status_code=404, detail="Provider not found")
            return LLMProviderResponse(
                id=provider.id,
                documentId=provider.document_id,
                name=provider.name or "",
                type=provider.type or "ollama",
                baseUrl=provider.base_url or "",
                apiKey=provider.api_key,
                defaultModel=provider.default_model,
                embeddingModel=provider.embedding_model,
                isActive=provider.is_active,
                isDefault=provider.is_default,
                description=provider.description
            )
        
        updates.append("updated_at = NOW()")
        values.append(provider_id)
        
        query = f"""
            UPDATE llm_providers 
            SET {', '.join(updates)}
            WHERE id = ${param_idx}
            RETURNING *
        """
        
        result = await db.fetch_one(query, *values)
        
        if not result:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        return LLMProviderResponse(
            id=result["id"],
            documentId=result.get("document_id"),
            name=result["name"] or "",
            type=result["type"] or "ollama",
            baseUrl=result["base_url"] or "",
            apiKey=result.get("api_key"),
            defaultModel=result.get("default_model"),
            embeddingModel=result.get("embedding_model"),
            isActive=result.get("is_active", True),
            isDefault=result.get("is_default", False),
            description=result.get("description")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/llm-providers/{provider_id}")
async def delete_llm_provider(provider_id: int):
    """Eliminar proveedor LLM"""
    try:
        db = get_db()
        await db.execute("DELETE FROM llm_providers WHERE id = $1", provider_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# MCP Connections
# ===========================================

@router.get("/mcp-connections", response_model=List[MCPConnectionResponse])
async def get_mcp_connections(active_only: bool = False):
    """Obtener lista de conexiones MCP"""
    try:
        connections = await MCPConnectionRepository.get_all(active_only=active_only)
        return [
            MCPConnectionResponse(
                id=c.id,
                documentId=c.document_id,
                name=c.name or "",
                type=c.type,
                serverUrl=c.server_url,
                command=c.command,
                args=c.args,
                isActive=c.is_active,
                description=c.description,
                config=c.config
            )
            for c in connections
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# Brain Chains
# ===========================================

@router.get("/brain-chains", response_model=List[BrainChainResponse])
async def get_brain_chains(active_only: bool = False):
    """Obtener lista de cadenas desde la BD"""
    try:
        chains = await ChainRepository.get_all(active_only=active_only)
        return [
            BrainChainResponse(
                id=c.id,
                documentId=c.document_id,
                name=c.name or "",
                slug=c.slug,
                type=c.type,
                description=c.description,
                version=c.version,
                isActive=c.is_active,
                handlerType=c.handler_type
            )
            for c in chains
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# API Keys
# ===========================================

@router.get("/api-keys", response_model=List[ApiKeyResponse])
async def get_api_keys(active_only: bool = False):
    """Obtener lista de API keys"""
    try:
        keys = await ApiKeyRepository.get_all(active_only=active_only)
        return [
            ApiKeyResponse(
                id=k.id,
                documentId=k.document_id,
                name=k.name or "",
                keyPrefix=k.key_prefix,
                key=k.key_prefix,  # Solo mostrar el prefix
                isActive=k.is_active,
                permissions=k.permissions,
                usageStats=k.usage_stats,
                expiresAt=k.expires_at.isoformat() if k.expires_at else None,
                createdByUser=k.created_by_user,
                notes=k.notes,
                createdAt=k.created_at.isoformat() if k.created_at else None
            )
            for k in keys
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CreateApiKeyRequest(BaseModel):
    name: str
    permissions: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class CreateApiKeyResponse(BaseModel):
    id: int
    key: str  # La key completa (solo se muestra una vez)
    keyPrefix: str
    name: str


@router.post("/api-keys", response_model=CreateApiKeyResponse)
async def create_api_key(request: CreateApiKeyRequest):
    """Crear nueva API key"""
    import secrets
    
    try:
        db = get_db()
        
        # Generar key aleatoria
        raw_key = "sk-brain-" + secrets.token_urlsafe(36)
        key_prefix = raw_key[:20]
        
        # Insertar en la base de datos
        query = """
            INSERT INTO brain_api_keys (name, key, key_prefix, is_active, permissions, usage_stats, notes, created_at, updated_at)
            VALUES ($1, $2, $3, true, $4, $5, $6, NOW(), NOW())
            RETURNING id
        """
        
        import json
        permissions_json = json.dumps(request.permissions or {
            "models": ["brain-adaptive", "brain-team"],
            "maxTokensPerRequest": 4096,
            "rateLimit": 60
        })
        usage_stats_json = json.dumps({
            "totalRequests": 0,
            "totalTokens": 0,
            "lastUsed": None
        })
        
        result = await db.fetch_one(
            query, 
            request.name, 
            raw_key,  # Guardar la key completa (o hash en producción)
            key_prefix, 
            permissions_json, 
            usage_stats_json, 
            request.notes or ""
        )
        
        return CreateApiKeyResponse(
            id=result["id"],
            key=raw_key,
            keyPrefix=key_prefix,
            name=request.name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UpdateApiKeyRequest(BaseModel):
    name: Optional[str] = None
    isActive: Optional[bool] = None
    permissions: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


@router.put("/api-keys/{key_id}")
async def update_api_key(key_id: int, request: UpdateApiKeyRequest):
    """Actualizar API key"""
    try:
        db = get_db()
        
        updates = []
        values = []
        param_idx = 1
        
        if request.name is not None:
            updates.append(f"name = ${param_idx}")
            values.append(request.name)
            param_idx += 1
        
        if request.isActive is not None:
            updates.append(f"is_active = ${param_idx}")
            values.append(request.isActive)
            param_idx += 1
        
        if request.permissions is not None:
            import json
            updates.append(f"permissions = ${param_idx}")
            values.append(json.dumps(request.permissions))
            param_idx += 1
        
        if request.notes is not None:
            updates.append(f"notes = ${param_idx}")
            values.append(request.notes)
            param_idx += 1
        
        if not updates:
            return {"success": True, "message": "No changes"}
        
        updates.append("updated_at = NOW()")
        values.append(key_id)
        
        query = f"""
            UPDATE brain_api_keys 
            SET {', '.join(updates)}
            WHERE id = ${param_idx}
        """
        
        await db.execute(query, *values)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api-keys/{key_id}")
async def delete_api_key(key_id: int):
    """Eliminar API key"""
    try:
        db = get_db()
        await db.execute("DELETE FROM brain_api_keys WHERE id = $1", key_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# Brain Settings
# ===========================================

class BrainSettingResponse(BaseModel):
    key: str
    value: Any
    type: str
    category: str
    label: Optional[str] = None
    description: Optional[str] = None
    isPublic: bool = True


class UpdateSettingRequest(BaseModel):
    value: Any


@router.get("/settings", response_model=List[BrainSettingResponse])
async def get_settings():
    """Obtener todos los settings del sistema"""
    try:
        rows = await BrainSettingsRepository.get_all()
        return [
            BrainSettingResponse(
                key=r["key"],
                value=r["value"],
                type=r["type"],
                category=r["category"],
                label=r.get("label"),
                description=r.get("description"),
                isPublic=r.get("is_public", True),
            )
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings/{key}", response_model=BrainSettingResponse)
async def update_setting(key: str, request: UpdateSettingRequest):
    """Actualizar el valor de un setting"""
    try:
        row = await BrainSettingsRepository.upsert(key, request.value)
        return BrainSettingResponse(
            key=row["key"],
            value=row["value"],
            type=row["type"],
            category=row["category"],
            label=row.get("label"),
            description=row.get("description"),
            isPublic=row.get("is_public", True),
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================================
# System Stats
# ===========================================

@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats():
    """Obtener estadísticas del sistema"""
    try:
        chains = await ChainRepository.get_all(active_only=True)
        providers = await LLMProviderRepository.get_all(active_only=True)
        mcp = await MCPConnectionRepository.get_all(active_only=True)
        api_keys = await ApiKeyRepository.get_all(active_only=True)
        openapi = await OpenAPIConnectionRepository.get_all(active_only=True)
        
        return SystemStatsResponse(
            chains=len(chains),
            llmProviders=len(providers),
            mcpConnections=len(mcp),
            apiKeys=len(api_keys),
            openApiConnections=len(openapi)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
