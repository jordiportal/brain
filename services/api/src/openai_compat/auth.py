"""
Authentication for OpenAI-Compatible API

Valida API keys contra Strapi y gestiona permisos.
"""

import os
import hashlib
import secrets
from typing import Optional, Dict, Any
from datetime import datetime
import httpx
import structlog

logger = structlog.get_logger()


class APIKeyValidator:
    """Validador de API keys para la API externa de Brain"""
    
    def __init__(self):
        self._strapi_url = os.getenv("STRAPI_URL", "http://strapi:1337")
        self._strapi_token = os.getenv("STRAPI_API_TOKEN")
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 300  # 5 minutos
    
    async def validate_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Valida una API key y retorna los datos del key si es válida.
        
        Args:
            api_key: La API key a validar (formato: sk-brain-xxx)
            
        Returns:
            Dict con datos del key si es válido, None si no
        """
        if not api_key:
            return None
        
        # Extraer prefijo para búsqueda
        key_prefix = api_key[:20] if len(api_key) > 20 else api_key
        
        # Verificar cache
        cached = self._cache.get(api_key)
        if cached:
            cache_time = cached.get("_cached_at", 0)
            if (datetime.now().timestamp() - cache_time) < self._cache_ttl:
                return cached if cached.get("isActive") else None
        
        # Buscar en Strapi
        try:
            key_data = await self._fetch_key_from_strapi(api_key)
            
            if key_data:
                # Validar que esté activo
                if not key_data.get("isActive", False):
                    logger.warning("API key is inactive", key_prefix=key_prefix)
                    return None
                
                # Validar expiración
                expires_at = key_data.get("expiresAt")
                if expires_at:
                    expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    if expiry < datetime.now(expiry.tzinfo):
                        logger.warning("API key has expired", key_prefix=key_prefix)
                        return None
                
                # Cachear
                key_data["_cached_at"] = datetime.now().timestamp()
                self._cache[api_key] = key_data
                
                logger.info("API key validated", key_prefix=key_prefix, name=key_data.get("name"))
                return key_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error validating API key: {e}", exc_info=True)
            return None
    
    async def _fetch_key_from_strapi(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Busca una API key en Strapi"""
        if not self._strapi_token:
            logger.warning("STRAPI_API_TOKEN not configured")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Buscar por key exacto
                response = await client.get(
                    f"{self._strapi_url}/api/brain-api-keys",
                    headers={"Authorization": f"Bearer {self._strapi_token}"},
                    params={
                        "filters[key][$eq]": api_key,
                        "populate": "*"
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Strapi returned {response.status_code}")
                    return None
                
                data = response.json()
                items = data.get("data", [])
                
                if items:
                    item = items[0]
                    return {
                        "id": item["id"],
                        **item.get("attributes", {})
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Error fetching key from Strapi: {e}")
            return None
    
    async def update_usage(self, api_key: str, tokens_used: int) -> None:
        """Actualiza las estadísticas de uso de una API key"""
        if not self._strapi_token:
            return
        
        # Obtener datos actuales del cache
        key_data = self._cache.get(api_key)
        if not key_data:
            return
        
        key_id = key_data.get("id")
        if not key_id:
            return
        
        try:
            # Obtener stats actuales
            current_stats = key_data.get("usageStats", {})
            new_stats = {
                "totalRequests": current_stats.get("totalRequests", 0) + 1,
                "totalTokens": current_stats.get("totalTokens", 0) + tokens_used,
                "lastUsed": datetime.now().isoformat()
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.put(
                    f"{self._strapi_url}/api/brain-api-keys/{key_id}",
                    headers={"Authorization": f"Bearer {self._strapi_token}"},
                    json={"data": {"usageStats": new_stats}}
                )
            
            # Actualizar cache
            key_data["usageStats"] = new_stats
            
        except Exception as e:
            logger.warning(f"Error updating usage stats: {e}")
    
    def check_model_permission(self, key_data: Dict[str, Any], model: str) -> bool:
        """Verifica si el key tiene permiso para usar un modelo"""
        permissions = key_data.get("permissions", {})
        allowed_models = permissions.get("models", [])
        
        if not allowed_models:
            return True  # Sin restricciones = todo permitido
        
        return model in allowed_models
    
    def get_rate_limit(self, key_data: Dict[str, Any]) -> int:
        """Obtiene el rate limit para un key"""
        permissions = key_data.get("permissions", {})
        return permissions.get("rateLimit", 60)
    
    def clear_cache(self):
        """Limpia el cache de keys"""
        self._cache.clear()


def generate_api_key() -> str:
    """Genera una nueva API key en formato sk-brain-xxx"""
    random_part = secrets.token_hex(24)
    return f"sk-brain-{random_part}"


def hash_api_key(api_key: str) -> str:
    """Genera un hash de una API key para almacenamiento seguro"""
    return hashlib.sha256(api_key.encode()).hexdigest()


# Instancia global
api_key_validator = APIKeyValidator()
