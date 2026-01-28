# ===========================================
# Database Models (Pydantic)
# ===========================================

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class BrainChain(BaseModel):
    """Brain chain/agent configuration."""
    id: int
    document_id: Optional[str] = None
    name: Optional[str] = None
    slug: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    definition: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None
    tools: Optional[List[str]] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None
    is_active: bool = True
    handler_type: Optional[str] = None
    legacy_builder_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    
    # Joined data
    llm_provider: Optional["LLMProvider"] = None
    
    class Config:
        from_attributes = True


class LLMProvider(BaseModel):
    """LLM Provider configuration."""
    id: int
    document_id: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None  # ollama, openai, anthropic, etc.
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    default_model: Optional[str] = None
    embedding_model: Optional[str] = None
    is_active: bool = True
    config: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class BrainApiKey(BaseModel):
    """API Key for OpenAI-compatible endpoint."""
    id: int
    document_id: Optional[str] = None
    name: Optional[str] = None
    key: Optional[str] = None
    key_prefix: Optional[str] = None
    is_active: bool = True
    permissions: Optional[Dict[str, Any]] = None
    usage_stats: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None
    created_by_user: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class BrainModelConfig(BaseModel):
    """Configuration for OpenAI-compatible model exposure."""
    id: int
    document_id: Optional[str] = None
    is_enabled: bool = False
    base_url: Optional[str] = None
    default_model: Optional[str] = None
    available_models: Optional[List[Dict[str, Any]]] = None
    backend_llm: Optional[Dict[str, Any]] = None
    rate_limits: Optional[Dict[str, Any]] = None
    logging_enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class OpenAPIConnection(BaseModel):
    """OpenAPI connection configuration."""
    id: int
    document_id: Optional[str] = None
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    spec_url: Optional[str] = None
    base_url: Optional[str] = None
    auth_type: Optional[str] = None  # none, bearer, api_key, basic
    auth_token: Optional[str] = None
    auth_header: Optional[str] = None
    auth_prefix: Optional[str] = None
    is_active: bool = True
    timeout: int = 30
    enabled_endpoints: Optional[List[str]] = None
    custom_headers: Optional[Dict[str, str]] = None
    last_sync_at: Optional[datetime] = None
    cached_spec: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ToolConfig(BaseModel):
    """Tool configuration."""
    id: int
    document_id: Optional[str] = None
    is_active: bool = True
    last_updated: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    
    # Component settings (from tool_configs_cmps)
    execution_settings: Optional[Dict[str, Any]] = None
    filesystem_settings: Optional[Dict[str, Any]] = None
    web_settings: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


class MCPConnection(BaseModel):
    """MCP Server connection configuration."""
    id: int
    document_id: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None  # stdio, http, sse
    command: Optional[str] = None
    args: Optional[List[str]] = None
    server_url: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    is_active: bool = True
    config: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
