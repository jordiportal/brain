# ===========================================
# OpenAPI Connections Repository
# ===========================================

import logging
from typing import Optional, List
from ..connection import get_db
from ..models import OpenAPIConnection

logger = logging.getLogger(__name__)


class OpenAPIConnectionRepository:
    """Repository for openapi_connections table."""
    
    @staticmethod
    async def get_all(active_only: bool = True) -> List[OpenAPIConnection]:
        """Get all OpenAPI connections."""
        db = get_db()
        
        query = "SELECT * FROM openapi_connections"
        if active_only:
            query += " WHERE is_active = true"
        query += " ORDER BY name"
        
        rows = await db.fetch_all(query)
        return [OpenAPIConnectionRepository._row_to_connection(row) for row in rows]
    
    @staticmethod
    async def get_by_id(connection_id: int) -> Optional[OpenAPIConnection]:
        """Get connection by ID."""
        db = get_db()
        
        query = "SELECT * FROM openapi_connections WHERE id = $1"
        row = await db.fetch_one(query, connection_id)
        
        if not row:
            return None
        
        return OpenAPIConnectionRepository._row_to_connection(row)
    
    @staticmethod
    async def get_by_slug(slug: str) -> Optional[OpenAPIConnection]:
        """Get connection by slug."""
        db = get_db()
        
        query = "SELECT * FROM openapi_connections WHERE slug = $1"
        row = await db.fetch_one(query, slug)
        
        if not row:
            return None
        
        return OpenAPIConnectionRepository._row_to_connection(row)
    
    @staticmethod
    async def get_by_name(name: str) -> Optional[OpenAPIConnection]:
        """Get connection by name."""
        db = get_db()
        
        query = "SELECT * FROM openapi_connections WHERE name = $1"
        row = await db.fetch_one(query, name)
        
        if not row:
            return None
        
        return OpenAPIConnectionRepository._row_to_connection(row)
    
    @staticmethod
    async def update_cached_spec(connection_id: int, cached_spec: dict) -> bool:
        """Update the cached OpenAPI spec."""
        db = get_db()
        
        try:
            import json
            
            query = """
                UPDATE openapi_connections 
                SET cached_spec = $1::jsonb, last_sync_at = NOW(), updated_at = NOW()
                WHERE id = $2
            """
            await db.execute(query, json.dumps(cached_spec), connection_id)
            return True
            
        except Exception as e:
            logger.error(f"Error updating cached spec: {e}")
            return False
    
    @staticmethod
    def _row_to_connection(row) -> OpenAPIConnection:
        """Convert database row to OpenAPIConnection model."""
        enabled_endpoints = row.get('enabled_endpoints')
        custom_headers = row.get('custom_headers')
        cached_spec = row.get('cached_spec')
        
        return OpenAPIConnection(
            id=row['id'],
            document_id=row.get('document_id'),
            name=row.get('name'),
            slug=row.get('slug'),
            description=row.get('description'),
            spec_url=row.get('spec_url'),
            base_url=row.get('base_url'),
            auth_type=row.get('auth_type'),
            auth_token=row.get('auth_token'),
            auth_header=row.get('auth_header'),
            auth_prefix=row.get('auth_prefix'),
            is_active=row.get('is_active', True),
            timeout=row.get('timeout', 30),
            enabled_endpoints=enabled_endpoints if isinstance(enabled_endpoints, list) else None,
            custom_headers=custom_headers if isinstance(custom_headers, dict) else None,
            last_sync_at=row.get('last_sync_at'),
            cached_spec=cached_spec if isinstance(cached_spec, dict) else None,
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
            published_at=row.get('published_at'),
        )
