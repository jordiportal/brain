# ===========================================
# Brain Chains Repository
# ===========================================

import json
import logging
from typing import Optional, List
from ..connection import get_db
from ..models import BrainChain, LLMProvider

logger = logging.getLogger(__name__)


class ChainRepository:
    """Repository for brain_chains table."""
    
    @staticmethod
    async def get_all(active_only: bool = True) -> List[BrainChain]:
        """Get all chains."""
        db = get_db()
        
        query = """
            SELECT c.*, p.id as provider_id, p.name as provider_name, 
                   p.type as provider_type, p.base_url as provider_base_url,
                   p.api_key as provider_api_key, p.default_model as provider_default_model,
                   p.is_active as provider_is_active, p.config as provider_config
            FROM brain_chains c
            LEFT JOIN brain_chains_llm_provider_lnk lnk ON c.id = lnk.brain_chain_id
            LEFT JOIN llm_providers p ON lnk.llm_provider_id = p.id
        """
        
        if active_only:
            query += " WHERE c.is_active = true"
        
        query += " ORDER BY c.name"
        
        rows = await db.fetch_all(query)
        chains = []
        
        for row in rows:
            chain = ChainRepository._row_to_chain(row)
            chains.append(chain)
        
        return chains
    
    @staticmethod
    async def get_by_id(chain_id: int) -> Optional[BrainChain]:
        """Get chain by ID."""
        db = get_db()
        
        query = """
            SELECT c.*, p.id as provider_id, p.name as provider_name, 
                   p.type as provider_type, p.base_url as provider_base_url,
                   p.api_key as provider_api_key, p.default_model as provider_default_model,
                   p.is_active as provider_is_active, p.config as provider_config
            FROM brain_chains c
            LEFT JOIN brain_chains_llm_provider_lnk lnk ON c.id = lnk.brain_chain_id
            LEFT JOIN llm_providers p ON lnk.llm_provider_id = p.id
            WHERE c.id = $1
        """
        
        row = await db.fetch_one(query, chain_id)
        if not row:
            return None
        
        return ChainRepository._row_to_chain(row)
    
    @staticmethod
    async def get_by_slug(slug: str) -> Optional[BrainChain]:
        """Get chain by slug."""
        db = get_db()
        
        query = """
            SELECT c.*, p.id as provider_id, p.name as provider_name, 
                   p.type as provider_type, p.base_url as provider_base_url,
                   p.api_key as provider_api_key, p.default_model as provider_default_model,
                   p.is_active as provider_is_active, p.config as provider_config
            FROM brain_chains c
            LEFT JOIN brain_chains_llm_provider_lnk lnk ON c.id = lnk.brain_chain_id
            LEFT JOIN llm_providers p ON lnk.llm_provider_id = p.id
            WHERE c.slug = $1
        """
        
        row = await db.fetch_one(query, slug)
        if not row:
            return None
        
        return ChainRepository._row_to_chain(row)
    
    @staticmethod
    async def get_by_name(name: str) -> Optional[BrainChain]:
        """Get chain by name."""
        db = get_db()
        
        query = """
            SELECT c.*, p.id as provider_id, p.name as provider_name, 
                   p.type as provider_type, p.base_url as provider_base_url,
                   p.api_key as provider_api_key, p.default_model as provider_default_model,
                   p.is_active as provider_is_active, p.config as provider_config
            FROM brain_chains c
            LEFT JOIN brain_chains_llm_provider_lnk lnk ON c.id = lnk.brain_chain_id
            LEFT JOIN llm_providers p ON lnk.llm_provider_id = p.id
            WHERE c.name = $1
        """
        
        row = await db.fetch_one(query, name)
        if not row:
            return None
        
        return ChainRepository._row_to_chain(row)
    
    @staticmethod
    async def update_llm_config(slug: str, provider_id: Optional[int], model: Optional[str]) -> bool:
        """Update default LLM configuration for a chain."""
        db = get_db()
        
        try:
            # Obtener la cadena actual
            chain = await ChainRepository.get_by_slug(slug)
            if not chain:
                return False
            
            # Actualizar config con los nuevos valores de LLM
            current_config = chain.config or {}
            current_config["default_llm_provider_id"] = provider_id
            current_config["default_llm_model"] = model
            
            # Guardar en la base de datos
            query = """
                UPDATE brain_chains 
                SET config = $1::jsonb, updated_at = NOW()
                WHERE slug = $2
            """
            
            await db.execute(query, json.dumps(current_config), slug)
            logger.info(f"Updated LLM config for chain {slug}: provider_id={provider_id}, model={model}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating LLM config for chain {slug}: {e}")
            return False
    
    @staticmethod
    async def update_system_prompt(slug: str, system_prompt: str) -> bool:
        """Update system prompt for a chain."""
        db = get_db()
        
        try:
            # Obtener la cadena actual
            chain = await ChainRepository.get_by_slug(slug)
            if not chain:
                return False
            
            # Actualizar prompts con el nuevo system prompt
            current_prompts = chain.prompts or {}
            current_prompts["system"] = system_prompt
            
            # Guardar en la base de datos
            query = """
                UPDATE brain_chains 
                SET prompts = $1::jsonb, updated_at = NOW()
                WHERE slug = $2
            """
            
            await db.execute(query, json.dumps(current_prompts), slug)
            logger.info(f"Updated system prompt for chain {slug}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating system prompt for chain {slug}: {e}")
            return False

    @staticmethod
    def _row_to_chain(row) -> BrainChain:
        """Convert database row to BrainChain model."""
        # Parse JSONB fields
        definition = row.get('definition')
        prompts = row.get('prompts')
        tools = row.get('tools')
        nodes = row.get('nodes')
        edges = row.get('edges')
        config = row.get('config')
        tags = row.get('tags')
        
        # Build LLM provider if present
        llm_provider = None
        if row.get('provider_id'):
            provider_config = row.get('provider_config')
            llm_provider = LLMProvider(
                id=row['provider_id'],
                name=row.get('provider_name'),
                type=row.get('provider_type'),
                base_url=row.get('provider_base_url'),
                api_key=row.get('provider_api_key'),
                default_model=row.get('provider_default_model'),
                is_active=row.get('provider_is_active', True),
                config=provider_config if isinstance(provider_config, dict) else None,
            )
        
        return BrainChain(
            id=row['id'],
            document_id=row.get('document_id'),
            name=row.get('name'),
            slug=row.get('slug'),
            type=row.get('type'),
            description=row.get('description'),
            version=row.get('version'),
            definition=definition if isinstance(definition, dict) else None,
            prompts=prompts if isinstance(prompts, dict) else None,
            tools=tools if isinstance(tools, list) else None,
            nodes=nodes if isinstance(nodes, list) else None,
            edges=edges if isinstance(edges, list) else None,
            is_active=row.get('is_active', True),
            handler_type=row.get('handler_type'),
            legacy_builder_id=row.get('legacy_builder_id'),
            config=config if isinstance(config, dict) else None,
            tags=tags if isinstance(tags, list) else None,
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
            published_at=row.get('published_at'),
            llm_provider=llm_provider,
        )
