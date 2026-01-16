"""
Configuración del módulo RAG
"""

from typing import Optional
from pydantic import BaseModel
from src.config import get_settings

settings = get_settings()


class RAGConfig(BaseModel):
    """Configuración para RAG"""
    
    # Embedding model (se sobrescribe con config de Strapi)
    embedding_model: str = "qwen3-embedding:8b"
    embedding_base_url: str = "http://host.docker.internal:11434"
    embedding_dimensions: int = 4096
    
    # Chunking
    chunk_size: int = 500
    chunk_overlap: int = 50
    
    # Vector store
    collection_name: str = "default"
    
    # Search
    default_top_k: int = 5
    similarity_threshold: float = 0.5  # Más permisivo


async def get_rag_config_from_strapi() -> RAGConfig:
    """Obtener configuración RAG desde Strapi LLM Provider"""
    from src.providers import get_active_llm_provider
    
    config = RAGConfig()
    
    provider = await get_active_llm_provider()
    if provider:
        config.embedding_base_url = provider.base_url
        if provider.embedding_model:
            config.embedding_model = provider.embedding_model
    
    return config


def get_rag_config() -> RAGConfig:
    """Obtener configuración RAG básica (sin Strapi)"""
    return RAGConfig()
