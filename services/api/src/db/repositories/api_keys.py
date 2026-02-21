# ===========================================
# Brain API Keys Repository
# ===========================================

import logging
from datetime import datetime
from typing import Optional, List
from ..connection import get_db
from ..models import BrainApiKey

logger = logging.getLogger(__name__)


class ApiKeyRepository:
    """Repository for brain_api_keys table."""
    
    @staticmethod
    async def get_all(active_only: bool = True) -> List[BrainApiKey]:
        """Get all API keys."""
        db = get_db()
        
        query = "SELECT * FROM brain_api_keys"
        if active_only:
            query += " WHERE is_active = true"
        query += " ORDER BY name"
        
        rows = await db.fetch_all(query)
        return [ApiKeyRepository._row_to_api_key(row) for row in rows]
    
    @staticmethod
    async def get_by_id(key_id: int) -> Optional[BrainApiKey]:
        """Get API key by ID."""
        db = get_db()
        
        query = "SELECT * FROM brain_api_keys WHERE id = $1"
        row = await db.fetch_one(query, key_id)
        
        if not row:
            return None
        
        return ApiKeyRepository._row_to_api_key(row)
    
    @staticmethod
    async def get_by_key(key: str) -> Optional[BrainApiKey]:
        """Get API key by the actual key value."""
        db = get_db()
        
        query = "SELECT * FROM brain_api_keys WHERE key = $1 AND is_active = true"
        row = await db.fetch_one(query, key)
        
        if not row:
            return None
        
        return ApiKeyRepository._row_to_api_key(row)
    
    @staticmethod
    async def validate_key(key: str) -> Optional[BrainApiKey]:
        """Validate an API key and check expiration."""
        api_key = await ApiKeyRepository.get_by_key(key)
        
        if not api_key:
            return None
        
        if not api_key.is_active:
            return None
        
        # Check expiration
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None
        
        return api_key
    
    @staticmethod
    async def update_usage(key_id: int, tokens_used: int) -> bool:
        """Update usage statistics for an API key."""
        db = get_db()
        
        try:
            # Get current usage stats
            query = "SELECT usage_stats FROM brain_api_keys WHERE id = $1"
            row = await db.fetch_one(query, key_id)
            
            if not row:
                return False
            
            current_stats = row.get('usage_stats') or {}
            if not isinstance(current_stats, dict):
                current_stats = {}
            
            # Update stats
            current_stats['total_tokens'] = current_stats.get('total_tokens', 0) + tokens_used
            current_stats['total_requests'] = current_stats.get('total_requests', 0) + 1
            current_stats['last_used'] = datetime.utcnow().isoformat()
            
            # Save
            import json
            update_query = """
                UPDATE brain_api_keys 
                SET usage_stats = $1::jsonb, updated_at = NOW() 
                WHERE id = $2
            """
            await db.execute(update_query, json.dumps(current_stats), key_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating API key usage: {e}")
            return False
    
    @staticmethod
    async def create(
        name: str,
        key: str,
        key_prefix: str,
        permissions: Optional[dict] = None,
        expires_at: Optional[datetime] = None,
        created_by_user: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Optional[BrainApiKey]:
        """Create a new API key."""
        db = get_db()
        
        try:
            import json
            import uuid
            
            document_id = str(uuid.uuid4())[:8]
            
            query = """
                INSERT INTO brain_api_keys 
                (document_id, name, key, key_prefix, is_active, permissions, 
                 usage_stats, expires_at, created_by_user, notes, 
                 created_at, updated_at, published_at)
                VALUES ($1, $2, $3, $4, true, $5::jsonb, $6::jsonb, $7, $8, $9, NOW(), NOW(), NOW())
                RETURNING *
            """
            
            row = await db.fetch_one(
                query,
                document_id,
                name,
                key,
                key_prefix,
                json.dumps(permissions or {"models": ["*"]}),
                json.dumps({"total_tokens": 0, "total_requests": 0}),
                expires_at,
                created_by_user,
                notes,
            )
            
            if not row:
                return None
            
            return ApiKeyRepository._row_to_api_key(row)
            
        except Exception as e:
            logger.error(f"Error creating API key: {e}")
            return None
    
    @staticmethod
    def _row_to_api_key(row) -> BrainApiKey:
        """Convert database row to BrainApiKey model."""
        permissions = row.get('permissions')
        usage_stats = row.get('usage_stats')
        if isinstance(permissions, str):
            import json as _json
            permissions = _json.loads(permissions)
        if isinstance(usage_stats, str):
            import json as _json
            usage_stats = _json.loads(usage_stats)
        
        return BrainApiKey(
            id=row['id'],
            document_id=row.get('document_id'),
            name=row.get('name'),
            key=row.get('key'),
            key_prefix=row.get('key_prefix'),
            is_active=row.get('is_active', True),
            permissions=permissions if isinstance(permissions, dict) else None,
            usage_stats=usage_stats if isinstance(usage_stats, dict) else None,
            expires_at=row.get('expires_at'),
            created_by_user=row.get('created_by_user'),
            notes=row.get('notes'),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
            published_at=row.get('published_at'),
        )
