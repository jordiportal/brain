"""
Obtener configuración de LLM Provider desde Strapi
"""

from typing import Optional
from dataclasses import dataclass
import httpx
import structlog

logger = structlog.get_logger()

# URL de Strapi (dentro de Docker network)
STRAPI_URL = "http://strapi:1337"

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
    Obtener el LLM Provider activo desde Strapi
    
    Returns:
        LLMProviderConfig si hay un provider activo, None si no
    """
    global _provider_cache, _cache_timestamp
    
    import time
    current_time = time.time()
    
    # Usar cache si está disponible y no ha expirado
    if use_cache and _provider_cache and (current_time - _cache_timestamp) < CACHE_TTL:
        return _provider_cache
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{STRAPI_URL}/api/llm-providers",
                params={"filters[isActive][$eq]": "true"}
            )
            
            if response.status_code != 200:
                logger.warning(f"Error obteniendo LLM providers: {response.status_code}")
                return _provider_cache  # Retornar cache anterior si existe
            
            data = response.json()
            providers = data.get("data", [])
            
            if not providers:
                logger.warning("No hay LLM providers activos en Strapi")
                return None
            
            # Tomar el primer provider activo
            provider = providers[0]
            
            config = LLMProviderConfig(
                id=provider.get("id"),
                document_id=provider.get("documentId", ""),
                name=provider.get("name", ""),
                type=provider.get("type", "ollama"),
                base_url=provider.get("baseUrl", ""),
                api_key=provider.get("apiKey"),
                default_model=provider.get("defaultModel", ""),
                embedding_model=provider.get("embeddingModel"),
                is_active=provider.get("isActive", False),
                config=provider.get("config") or {}
            )
            
            # Actualizar cache
            _provider_cache = config
            _cache_timestamp = current_time
            
            logger.info(f"LLM Provider cargado: {config.name} ({config.base_url})")
            return config
            
    except Exception as e:
        logger.error(f"Error conectando con Strapi: {e}")
        return _provider_cache  # Retornar cache anterior si existe


def get_active_llm_provider_sync() -> Optional[LLMProviderConfig]:
    """
    Versión síncrona para obtener el LLM Provider
    """
    global _provider_cache, _cache_timestamp
    
    import time
    current_time = time.time()
    
    if _provider_cache and (current_time - _cache_timestamp) < CACHE_TTL:
        return _provider_cache
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{STRAPI_URL}/api/llm-providers",
                params={"filters[isActive][$eq]": "true"}
            )
            
            if response.status_code != 200:
                return _provider_cache
            
            data = response.json()
            providers = data.get("data", [])
            
            if not providers:
                return None
            
            provider = providers[0]
            
            config = LLMProviderConfig(
                id=provider.get("id"),
                document_id=provider.get("documentId", ""),
                name=provider.get("name", ""),
                type=provider.get("type", "ollama"),
                base_url=provider.get("baseUrl", ""),
                api_key=provider.get("apiKey"),
                default_model=provider.get("defaultModel", ""),
                embedding_model=provider.get("embeddingModel"),
                is_active=provider.get("isActive", False),
                config=provider.get("config") or {}
            )
            
            _provider_cache = config
            _cache_timestamp = current_time
            
            return config
            
    except Exception as e:
        logger.error(f"Error conectando con Strapi (sync): {e}")
        return _provider_cache


def clear_provider_cache():
    """Limpiar cache de provider"""
    global _provider_cache, _cache_timestamp
    _provider_cache = None
    _cache_timestamp = 0
