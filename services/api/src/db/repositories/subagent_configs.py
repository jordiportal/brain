# ===========================================
# Subagent Configs Repository
# ===========================================

import logging
import json
from typing import Optional, List, Dict, Any
from ..connection import get_db
from ..models import SubagentConfig

logger = logging.getLogger(__name__)


class SubagentConfigRepository:
    """Repository for subagent_configs table."""
    
    @staticmethod
    async def get_all() -> List[SubagentConfig]:
        """Get all subagent configurations."""
        db = get_db()
        
        query = "SELECT * FROM subagent_configs ORDER BY agent_id"
        rows = await db.fetch_all(query)
        return [SubagentConfigRepository._row_to_config(row) for row in rows]
    
    @staticmethod
    async def get_by_agent_id(agent_id: str) -> Optional[SubagentConfig]:
        """Get configuration for a specific subagent."""
        db = get_db()
        
        query = "SELECT * FROM subagent_configs WHERE agent_id = $1"
        row = await db.fetch_one(query, agent_id)
        
        if not row:
            return None
        
        return SubagentConfigRepository._row_to_config(row)
    
    @staticmethod
    async def upsert(
        agent_id: str,
        is_enabled: bool = True,
        llm_provider_id: Optional[int] = None,
        llm_model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> SubagentConfig:
        """
        Insert or update subagent configuration.
        Uses UPSERT (INSERT ... ON CONFLICT UPDATE).
        """
        db = get_db()
        
        settings_json = json.dumps(settings) if settings else None
        
        query = """
            INSERT INTO subagent_configs (agent_id, is_enabled, llm_provider_id, llm_model, system_prompt, settings, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
            ON CONFLICT (agent_id) 
            DO UPDATE SET 
                is_enabled = EXCLUDED.is_enabled,
                llm_provider_id = EXCLUDED.llm_provider_id,
                llm_model = EXCLUDED.llm_model,
                system_prompt = COALESCE(EXCLUDED.system_prompt, subagent_configs.system_prompt),
                settings = COALESCE(EXCLUDED.settings, subagent_configs.settings),
                updated_at = NOW()
            RETURNING *
        """
        
        row = await db.fetch_one(
            query, 
            agent_id, 
            is_enabled, 
            llm_provider_id, 
            llm_model, 
            system_prompt,
            settings_json
        )
        
        return SubagentConfigRepository._row_to_config(row)
    
    @staticmethod
    async def update_system_prompt(agent_id: str, system_prompt: str) -> bool:
        """Update only the system prompt for a subagent."""
        db = get_db()
        
        # Primero verificar si existe, si no crear con defaults
        existing = await SubagentConfigRepository.get_by_agent_id(agent_id)
        if not existing:
            await SubagentConfigRepository.upsert(
                agent_id=agent_id,
                system_prompt=system_prompt
            )
            return True
        
        query = """
            UPDATE subagent_configs 
            SET system_prompt = $2, updated_at = NOW()
            WHERE agent_id = $1
        """
        await db.execute(query, agent_id, system_prompt)
        return True
    
    @staticmethod
    async def delete(agent_id: str) -> bool:
        """Delete subagent configuration."""
        db = get_db()
        
        query = "DELETE FROM subagent_configs WHERE agent_id = $1"
        await db.execute(query, agent_id)
        return True
    
    @staticmethod
    def _row_to_config(row) -> SubagentConfig:
        """Convert database row to SubagentConfig model."""
        settings = row.get('settings')
        
        # Parse JSON si viene como string
        if isinstance(settings, str):
            try:
                settings = json.loads(settings)
            except (json.JSONDecodeError, TypeError):
                settings = None
        
        return SubagentConfig(
            id=row['id'],
            agent_id=row.get('agent_id'),
            is_enabled=row.get('is_enabled', True),
            llm_provider_id=row.get('llm_provider_id'),
            llm_model=row.get('llm_model'),
            system_prompt=row.get('system_prompt'),
            settings=settings if isinstance(settings, dict) else None,
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
        )
