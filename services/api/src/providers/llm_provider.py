"""
Obtener configuración de LLM Provider desde PostgreSQL directamente
"""

import time
from typing import Optional
from dataclasses import dataclass
import structlog

from ..db.repositories import LLMProviderRepository

logger = structlog.get_logger()

# Cache simple para evitar llamadas repetidas
_provider_cache: Optional["LLMProviderConfig"] = None
_cache_timestamp: float = 0
CACHE_TTL = 60  # segundos


@dataclass
class LLMProviderConfig:
    """Configuración de un LLM Provider"""
    id: int
    document_id: str
    name: str
    type: str
    base_url: str
    api_key: Optional[str]
    default_model: str
    embedding_model: Optional[str]
    is_active: bool
    config: dict


async def get_active_llm_provider(use_cache: bool = True) -> Optional[LLMProviderConfig]:
    """
    Obtener el LLM Provider activo desde PostgreSQL
    
    Returns:
        LLMProviderConfig si hay un provider activo, None si no
    """
    global _provider_cache, _cache_timestamp
    
    current_time = time.time()
    
    # Usar cache si está disponible y no ha expirado
    if use_cache and _provider_cache and (current_time - _cache_timestamp) < CACHE_TTL:
        return _provider_cache
    
    try:
        provider = await LLMProviderRepository.get_default()
        
        if not provider:
            logger.warning("No hay LLM providers activos en la BD")
            return None
        
        config = LLMProviderConfig(
            id=provider.id,
            document_id=provider.document_id or "",
            name=provider.name or "",
            type=provider.type or "ollama",
            base_url=provider.base_url or "",
            api_key=provider.api_key,
            default_model=provider.default_model or "",
            embedding_model=provider.embedding_model,
            is_active=provider.is_active,
            config=provider.config or {}
        )
        
        # Actualizar cache
        _provider_cache = config
        _cache_timestamp = current_time
        
        logger.info(f"LLM Provider cargado: {config.name} ({config.type})")
        return config
            
    except Exception as e:
        logger.error(f"Error obteniendo LLM provider: {e}")
        return _provider_cache  # Retornar cache anterior si existe


async def get_provider_by_type(provider_type: str, use_cache: bool = False) -> Optional[LLMProviderConfig]:
    """
    Obtener un LLM Provider específico por tipo desde PostgreSQL
    
    Args:
        provider_type: Tipo de provider (ollama, openai, anthropic, etc.)
        use_cache: Si usar cache (por defecto False para búsquedas específicas)
    
    Returns:
        LLMProviderConfig si se encuentra, None si no
    """
    try:
        providers = await LLMProviderRepository.get_by_type(provider_type)
        
        if not providers:
            logger.warning(f"No hay provider activo de tipo {provider_type}")
            return None
        
        provider = providers[0]
        
        config = LLMProviderConfig(
            id=provider.id,
            document_id=provider.document_id or "",
            name=provider.name or "",
            type=provider.type or "ollama",
            base_url=provider.base_url or "",
            api_key=provider.api_key,
            default_model=provider.default_model or "",
            embedding_model=provider.embedding_model,
            is_active=provider.is_active,
            config=provider.config or {}
        )
        
        logger.info(f"Provider {provider_type} encontrado: {config.name}")
        return config
            
    except Exception as e:
        logger.error(f"Error obteniendo provider {provider_type}: {e}")
        return None


def get_active_llm_provider_sync() -> Optional[LLMProviderConfig]:
    """
    Versión síncrona para obtener el LLM Provider (usa cache)
    """
    global _provider_cache, _cache_timestamp
    
    current_time = time.time()
    
    if _provider_cache and (current_time - _cache_timestamp) < CACHE_TTL:
        return _provider_cache
    
    # En versión sync, solo retornamos cache si existe
    # El cache se actualiza desde llamadas async
    logger.warning("get_active_llm_provider_sync: Cache vacío, usar versión async")
    return _provider_cache


def clear_provider_cache():
    """Limpiar cache de provider"""
    global _provider_cache, _cache_timestamp
    _provider_cache = None
    _cache_timestamp = 0
