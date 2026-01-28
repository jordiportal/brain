# ===========================================
# LLM Providers Repository
# ===========================================

import logging
from typing import Optional, List
from ..connection import get_db
from ..models import LLMProvider

logger = logging.getLogger(__name__)


class LLMProviderRepository:
    """Repository for llm_providers table."""
    
    @staticmethod
    async def get_all(active_only: bool = True) -> List[LLMProvider]:
        """Get all LLM providers."""
        db = get_db()
        
        query = "SELECT * FROM llm_providers"
        if active_only:
            query += " WHERE is_active = true"
        query += " ORDER BY name"
        
        rows = await db.fetch_all(query)
        return [LLMProviderRepository._row_to_provider(row) for row in rows]
    
    @staticmethod
    async def get_by_id(provider_id: int) -> Optional[LLMProvider]:
        """Get provider by ID."""
        db = get_db()
        
        query = "SELECT * FROM llm_providers WHERE id = $1"
        row = await db.fetch_one(query, provider_id)
        
        if not row:
            return None
        
        return LLMProviderRepository._row_to_provider(row)
    
    @staticmethod
    async def get_by_name(name: str) -> Optional[LLMProvider]:
        """Get provider by name."""
        db = get_db()
        
        query = "SELECT * FROM llm_providers WHERE name = $1"
        row = await db.fetch_one(query, name)
        
        if not row:
            return None
        
        return LLMProviderRepository._row_to_provider(row)
    
    @staticmethod
    async def get_by_type(provider_type: str) -> List[LLMProvider]:
        """Get providers by type (ollama, openai, anthropic, etc.)."""
        db = get_db()
        
        query = "SELECT * FROM llm_providers WHERE type = $1 AND is_active = true ORDER BY name"
        rows = await db.fetch_all(query, provider_type)
        
        return [LLMProviderRepository._row_to_provider(row) for row in rows]
    
    @staticmethod
    async def get_default() -> Optional[LLMProvider]:
        """Get the first active provider (as default)."""
        db = get_db()
        
        query = "SELECT * FROM llm_providers WHERE is_active = true ORDER BY id LIMIT 1"
        row = await db.fetch_one(query)
        
        if not row:
            return None
        
        return LLMProviderRepository._row_to_provider(row)
    
    @staticmethod
    def _row_to_provider(row) -> LLMProvider:
        """Convert database row to LLMProvider model."""
        config = row.get('config')
        
        return LLMProvider(
            id=row['id'],
            document_id=row.get('document_id'),
            name=row.get('name'),
            type=row.get('type'),
            base_url=row.get('base_url'),
            api_key=row.get('api_key'),
            default_model=row.get('default_model'),
            embedding_model=row.get('embedding_model'),
            is_active=row.get('is_active', True),
            config=config if isinstance(config, dict) else None,
            description=row.get('description'),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
            published_at=row.get('published_at'),
        )
