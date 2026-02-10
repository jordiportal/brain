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
    async def update(connection_id: int, connection_data: dict) -> Optional[OpenAPIConnection]:
        """Update an existing OpenAPI connection."""
        db = get_db()
        
        try:
            import json
            
            # Check if connection exists
            existing = await OpenAPIConnectionRepository.get_by_id(connection_id)
            if not existing:
                return None
            
            query = """
                UPDATE openapi_connections 
                SET 
                    name = $1,
                    slug = $2,
                    description = $3,
                    spec_url = $4,
                    base_url = $5,
                    auth_type = $6,
                    auth_token = $7,
                    auth_header = $8,
                    auth_prefix = $9,
                    is_active = $10,
                    timeout = $11,
                    enabled_endpoints = $12::jsonb,
                    custom_headers = $13::jsonb,
                    updated_at = NOW()
                WHERE id = $14
                RETURNING *
            """
            
            row = await db.fetch_one(
                query,
                connection_data.get('name', existing.name),
                connection_data.get('slug', existing.slug),
                connection_data.get('description', existing.description),
                connection_data.get('spec_url', existing.spec_url),
                connection_data.get('base_url', existing.base_url),
                connection_data.get('auth_type', existing.auth_type),
                connection_data.get('auth_token', existing.auth_token),
                connection_data.get('auth_header', existing.auth_header),
                connection_data.get('auth_prefix', existing.auth_prefix),
                connection_data.get('is_active', existing.is_active),
                connection_data.get('timeout', existing.timeout),
                json.dumps(connection_data.get('enabled_endpoints', existing.enabled_endpoints or [])),
                json.dumps(connection_data.get('custom_headers', existing.custom_headers or {})),
                connection_id
            )
            
            if row:
                return OpenAPIConnectionRepository._row_to_connection(row)
            return None
            
        except Exception as e:
            logger.error(f"Error updating OpenAPI connection {connection_id}: {e}")
            return None
    
    @staticmethod
    async def create(connection_data: dict) -> Optional[OpenAPIConnection]:
        """Create a new OpenAPI connection."""
        db = get_db()
        
        try:
            import json
            
            query = """
                INSERT INTO openapi_connections (
                    name, slug, description, spec_url, base_url, 
                    auth_type, auth_token, auth_header, auth_prefix,
                    is_active, timeout, enabled_endpoints, custom_headers,
                    created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, $7, $8, $9,
                    $10, $11, $12::jsonb, $13::jsonb,
                    NOW(), NOW()
                )
                RETURNING *
            """
            
            row = await db.fetch_one(
                query,
                connection_data.get('name'),
                connection_data.get('slug'),
                connection_data.get('description'),
                connection_data.get('spec_url'),
                connection_data.get('base_url'),
                connection_data.get('auth_type', 'none'),
                connection_data.get('auth_token'),
                connection_data.get('auth_header', 'Authorization'),
                connection_data.get('auth_prefix', 'Bearer'),
                connection_data.get('is_active', True),
                connection_data.get('timeout', 30),
                json.dumps(connection_data.get('enabled_endpoints', [])),
                json.dumps(connection_data.get('custom_headers', {}))
            )
            
            if row:
                return OpenAPIConnectionRepository._row_to_connection(row)
            return None
            
        except Exception as e:
            logger.error(f"Error creating OpenAPI connection: {e}")
            return None
    
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
