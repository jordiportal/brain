# ===========================================
# Brain Chains Repository
# ===========================================

import json
import logging
from typing import Optional, List, Dict, Any
from ..connection import get_db
from ..models import BrainChain, LLMProvider, ChainVersion

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
    async def upsert(slug: str, name: str, chain_type: str, description: str = "",
                     version: str = "1.0.0", nodes: Optional[List] = None,
                     edges: Optional[List] = None, config: Optional[dict] = None,
                     prompts: Optional[dict] = None) -> bool:
        """Create or update a chain by slug."""
        db = get_db()
        
        try:
            # Verificar si existe
            existing = await ChainRepository.get_by_slug(slug)
            
            if existing:
                # Update
                query = """
                    UPDATE brain_chains 
                    SET name = $1, type = $2, description = $3, version = $4,
                        nodes = $5::jsonb, edges = $6::jsonb, config = $7::jsonb,
                        prompts = $8::jsonb, updated_at = NOW()
                    WHERE slug = $9
                """
                await db.execute(query, 
                    name, chain_type, description, version,
                    json.dumps(nodes or []), json.dumps(edges or []),
                    json.dumps(config or {}), json.dumps(prompts or {}),
                    slug
                )
                logger.info(f"Updated chain {slug}")
            else:
                # Insert
                query = """
                    INSERT INTO brain_chains (slug, name, type, description, version,
                        nodes, edges, config, prompts, is_active, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, $8::jsonb, $9::jsonb,
                        true, NOW(), NOW())
                """
                await db.execute(query,
                    slug, name, chain_type, description, version,
                    json.dumps(nodes or []), json.dumps(edges or []),
                    json.dumps(config or {}), json.dumps(prompts or {})
                )
                logger.info(f"Created chain {slug}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error upserting chain {slug}: {e}")
            return False
    
    @staticmethod
    async def update_llm_config(slug: str, provider_id: Optional[int], model: Optional[str]) -> bool:
        """Update default LLM configuration for a chain."""
        db = get_db()
        
        try:
            # Obtener la cadena actual o crear config base
            chain = await ChainRepository.get_by_slug(slug)
            current_config = (chain.config if chain else {}) or {}
            current_config["default_llm_provider_id"] = provider_id
            current_config["default_llm_model"] = model
            
            if chain:
                # Update existing
                query = """
                    UPDATE brain_chains 
                    SET config = $1::jsonb, updated_at = NOW()
                    WHERE slug = $2
                """
                await db.execute(query, json.dumps(current_config), slug)
            else:
                # Create new chain with minimal info
                await ChainRepository.upsert(
                    slug=slug,
                    name=slug.replace("_", " ").title(),
                    chain_type="agent",
                    config=current_config
                )
            
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
            # Obtener la cadena actual o crear prompts base
            chain = await ChainRepository.get_by_slug(slug)
            current_prompts = (chain.prompts if chain else {}) or {}
            current_prompts["system"] = system_prompt
            
            if chain:
                # Update existing
                query = """
                    UPDATE brain_chains 
                    SET prompts = $1::jsonb, updated_at = NOW()
                    WHERE slug = $2
                """
                await db.execute(query, json.dumps(current_prompts), slug)
            else:
                # Create new chain with minimal info
                await ChainRepository.upsert(
                    slug=slug,
                    name=slug.replace("_", " ").title(),
                    chain_type="agent",
                    prompts=current_prompts
                )
            
            logger.info(f"Updated system prompt for chain {slug}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating system prompt for chain {slug}: {e}")
            return False

    @staticmethod
    async def full_update(slug: str, data: Dict[str, Any]) -> bool:
        """Full update of a chain with versioning support."""
        db = get_db()
        try:
            existing = await ChainRepository.get_by_slug(slug)
            if not existing:
                return False

            change_reason = data.pop("change_reason", None)
            await ChainRepository.save_version(
                existing.id,
                {
                    "name": existing.name, "description": existing.description,
                    "version": existing.version, "type": existing.type,
                    "prompts": existing.prompts, "tools": existing.tools,
                    "config": existing.config, "nodes": existing.nodes,
                    "edges": existing.edges, "tags": existing.tags,
                },
                reason=change_reason,
            )

            set_clauses = []
            params: list = []
            idx = 1

            simple_fields = {"name": "name", "description": "description", "version": "version"}
            for key, col in simple_fields.items():
                if key in data:
                    set_clauses.append(f"{col} = ${idx}")
                    params.append(data[key])
                    idx += 1

            json_fields = {"prompts": "prompts", "config": "config", "nodes": "nodes", "edges": "edges", "tags": "tags"}
            for key, col in json_fields.items():
                if key in data:
                    set_clauses.append(f"{col} = ${idx}::jsonb")
                    params.append(json.dumps(data[key], ensure_ascii=False, default=str))
                    idx += 1

            if "tools" in data:
                set_clauses.append(f"tools = ${idx}::jsonb")
                params.append(json.dumps(data["tools"] or [], ensure_ascii=False))
                idx += 1

            if not set_clauses:
                return True

            set_clauses.append("updated_at = NOW()")
            params.append(slug)
            query = f"UPDATE brain_chains SET {', '.join(set_clauses)} WHERE slug = ${idx}"
            await db.execute(query, *params)
            logger.info(f"Full-updated chain {slug}")
            return True
        except Exception as e:
            logger.error(f"Error full-updating chain {slug}: {e}")
            return False

    @staticmethod
    async def delete(slug: str) -> bool:
        """Delete a chain by slug."""
        db = get_db()
        try:
            chain = await ChainRepository.get_by_slug(slug)
            if chain:
                await db.execute("DELETE FROM chain_versions WHERE brain_chain_id = $1", chain.id)
            await db.execute("DELETE FROM brain_chains_llm_provider_lnk WHERE brain_chain_id IN (SELECT id FROM brain_chains WHERE slug = $1)", slug)
            await db.execute("DELETE FROM brain_chains WHERE slug = $1", slug)
            logger.info(f"Deleted chain {slug}")
            return True
        except Exception as e:
            logger.error(f"Error deleting chain {slug}: {e}")
            return False

    # ---------- chain_versions ----------

    @staticmethod
    async def save_version(chain_id: int, snapshot: Dict[str, Any],
                           changed_by: Optional[str] = None, reason: Optional[str] = None) -> Optional[ChainVersion]:
        db = get_db()
        try:
            next_row = await db.fetch_one(
                "SELECT COALESCE(MAX(version_number), 0) + 1 AS next_num FROM chain_versions WHERE brain_chain_id = $1",
                chain_id,
            )
            next_num = next_row["next_num"] if next_row else 1
            row = await db.fetch_one(
                """INSERT INTO chain_versions (brain_chain_id, version_number, snapshot, changed_by, change_reason, created_at)
                   VALUES ($1, $2, $3::jsonb, $4, $5, NOW()) RETURNING *""",
                chain_id, next_num,
                json.dumps(snapshot, ensure_ascii=False, default=str),
                changed_by, reason,
            )
            return ChainRepository._row_to_version(row) if row else None
        except Exception as e:
            logger.error(f"Error saving chain version for id={chain_id}: {e}")
            return None

    @staticmethod
    async def get_versions(slug: str) -> List[ChainVersion]:
        db = get_db()
        chain = await ChainRepository.get_by_slug(slug)
        if not chain:
            return []
        rows = await db.fetch_all(
            "SELECT * FROM chain_versions WHERE brain_chain_id = $1 ORDER BY version_number DESC",
            chain.id,
        )
        return [ChainRepository._row_to_version(r) for r in rows]

    @staticmethod
    async def restore_version(slug: str, version_number: int) -> bool:
        db = get_db()
        chain = await ChainRepository.get_by_slug(slug)
        if not chain:
            return False
        ver_row = await db.fetch_one(
            "SELECT * FROM chain_versions WHERE brain_chain_id = $1 AND version_number = $2",
            chain.id, version_number,
        )
        if not ver_row:
            return False
        snapshot = ver_row["snapshot"]
        if isinstance(snapshot, str):
            snapshot = json.loads(snapshot)
        restore_data = {k: snapshot[k] for k in ("name", "description", "version", "prompts", "tools", "config", "nodes", "edges", "tags") if k in snapshot}
        restore_data["change_reason"] = f"Restored from version {version_number}"
        return await ChainRepository.full_update(slug, restore_data)

    @staticmethod
    def _row_to_version(row) -> ChainVersion:
        snapshot = row.get("snapshot", {})
        if isinstance(snapshot, str):
            try:
                snapshot = json.loads(snapshot)
            except (json.JSONDecodeError, TypeError):
                snapshot = {}
        return ChainVersion(
            id=row["id"],
            brain_chain_id=row["brain_chain_id"],
            version_number=row["version_number"],
            snapshot=snapshot if isinstance(snapshot, dict) else {},
            changed_by=row.get("changed_by"),
            change_reason=row.get("change_reason"),
            created_at=row.get("created_at"),
        )

    @staticmethod
    def _parse_jsonb(val):
        """Parse a JSONB field that may come as str from the DB driver."""
        if val is None:
            return None
        if isinstance(val, (dict, list)):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    @staticmethod
    def _row_to_chain(row) -> BrainChain:
        """Convert database row to BrainChain model."""
        parse = ChainRepository._parse_jsonb

        definition = parse(row.get('definition'))
        prompts = parse(row.get('prompts'))
        tools = parse(row.get('tools'))
        nodes = parse(row.get('nodes'))
        edges = parse(row.get('edges'))
        config = parse(row.get('config'))
        tags = parse(row.get('tags'))

        llm_provider = None
        if row.get('provider_id'):
            provider_config = parse(row.get('provider_config'))
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
