"""
Authentication for OpenAI-Compatible API

Valida API keys contra PostgreSQL directamente.
"""

import hashlib
import secrets
from typing import Optional, Dict, Any
from datetime import datetime
import structlog

from ..db.repositories import ApiKeyRepository

logger = structlog.get_logger()


class APIKeyValidator:
    """Validador de API keys para la API externa de Brain"""
    
    def __init__(self):
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
        
        # Extraer prefijo para logging
        key_prefix = api_key[:20] if len(api_key) > 20 else api_key
        
        # Verificar cache
        cached = self._cache.get(api_key)
        if cached:
            cache_time = cached.get("_cached_at", 0)
            if (datetime.now().timestamp() - cache_time) < self._cache_ttl:
                return cached if cached.get("is_active") else None
        
        # Buscar en PostgreSQL directamente
        try:
            key_data = await ApiKeyRepository.validate_key(api_key)
            
            if key_data:
                # Convertir a dict para compatibilidad
                data_dict = {
                    "id": key_data.id,
                    "name": key_data.name,
                    "key": key_data.key,
                    "keyPrefix": key_data.key_prefix,
                    "is_active": key_data.is_active,
                    "isActive": key_data.is_active,  # Compatibilidad
                    "permissions": key_data.permissions or {},
                    "usageStats": key_data.usage_stats or {},
                    "expiresAt": key_data.expires_at.isoformat() if key_data.expires_at else None,
                    "createdByUser": key_data.created_by_user,
                    "notes": key_data.notes,
                }
                
                # Cachear
                data_dict["_cached_at"] = datetime.now().timestamp()
                self._cache[api_key] = data_dict
                
                logger.info("API key validated", key_prefix=key_prefix, name=key_data.name)
                return data_dict
            
            logger.warning("API key not found or invalid", key_prefix=key_prefix)
            return None
            
        except Exception as e:
            logger.error(f"Error validating API key: {e}", exc_info=True)
            return None
    
    async def update_usage(self, api_key: str, tokens_used: int) -> None:
        """Actualiza las estadísticas de uso de una API key"""
        # Obtener datos actuales del cache
        key_data = self._cache.get(api_key)
        if not key_data:
            return
        
        key_id = key_data.get("id")
        if not key_id:
            return
        
        try:
            # Actualizar en BD
            await ApiKeyRepository.update_usage(key_id, tokens_used)
            
            # Actualizar cache
            current_stats = key_data.get("usageStats", {})
            key_data["usageStats"] = {
                "total_requests": current_stats.get("total_requests", 0) + 1,
                "total_tokens": current_stats.get("total_tokens", 0) + tokens_used,
                "last_used": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.warning(f"Error updating usage stats: {e}")
    
    def check_model_permission(self, key_data: Dict[str, Any], model: str) -> bool:
        """Verifica si el key tiene permiso para usar un modelo"""
        permissions = key_data.get("permissions", {})
        allowed_models = permissions.get("models", [])
        
        if not allowed_models or "*" in allowed_models:
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
