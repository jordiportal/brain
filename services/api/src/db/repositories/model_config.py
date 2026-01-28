# ===========================================
# Brain Model Config Repository
# ===========================================

import logging
from typing import Optional
from ..connection import get_db
from ..models import BrainModelConfig

logger = logging.getLogger(__name__)


class ModelConfigRepository:
    """Repository for brain_model_configs table (singleton config)."""
    
    @staticmethod
    async def get() -> Optional[BrainModelConfig]:
        """Get the model configuration (singleton)."""
        db = get_db()
        
        query = "SELECT * FROM brain_model_configs ORDER BY id LIMIT 1"
        row = await db.fetch_one(query)
        
        if not row:
            return None
        
        return ModelConfigRepository._row_to_config(row)
    
    @staticmethod
    async def update(
        is_enabled: Optional[bool] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        available_models: Optional[list] = None,
        backend_llm: Optional[dict] = None,
        rate_limits: Optional[dict] = None,
        logging_enabled: Optional[bool] = None,
    ) -> Optional[BrainModelConfig]:
        """Update the model configuration."""
        db = get_db()
        
        try:
            import json
            
            # Build update query dynamically
            updates = []
            params = []
            param_idx = 1
            
            if is_enabled is not None:
                updates.append(f"is_enabled = ${param_idx}")
                params.append(is_enabled)
                param_idx += 1
            
            if base_url is not None:
                updates.append(f"base_url = ${param_idx}")
                params.append(base_url)
                param_idx += 1
            
            if default_model is not None:
                updates.append(f"default_model = ${param_idx}")
                params.append(default_model)
                param_idx += 1
            
            if available_models is not None:
                updates.append(f"available_models = ${param_idx}::jsonb")
                params.append(json.dumps(available_models))
                param_idx += 1
            
            if backend_llm is not None:
                updates.append(f"backend_llm = ${param_idx}::jsonb")
                params.append(json.dumps(backend_llm))
                param_idx += 1
            
            if rate_limits is not None:
                updates.append(f"rate_limits = ${param_idx}::jsonb")
                params.append(json.dumps(rate_limits))
                param_idx += 1
            
            if logging_enabled is not None:
                updates.append(f"logging_enabled = ${param_idx}")
                params.append(logging_enabled)
                param_idx += 1
            
            if not updates:
                return await ModelConfigRepository.get()
            
            updates.append("updated_at = NOW()")
            
            query = f"""
                UPDATE brain_model_configs 
                SET {', '.join(updates)}
                WHERE id = (SELECT id FROM brain_model_configs ORDER BY id LIMIT 1)
                RETURNING *
            """
            
            row = await db.fetch_one(query, *params)
            
            if not row:
                return None
            
            return ModelConfigRepository._row_to_config(row)
            
        except Exception as e:
            logger.error(f"Error updating model config: {e}")
            return None
    
    @staticmethod
    async def create_if_not_exists() -> BrainModelConfig:
        """Create default config if none exists."""
        db = get_db()
        
        existing = await ModelConfigRepository.get()
        if existing:
            return existing
        
        try:
            import json
            import uuid
            
            document_id = str(uuid.uuid4())[:8]
            
            query = """
                INSERT INTO brain_model_configs 
                (document_id, is_enabled, base_url, default_model, 
                 available_models, backend_llm, rate_limits, logging_enabled,
                 created_at, updated_at, published_at)
                VALUES ($1, false, '', 'brain-default', $2::jsonb, $3::jsonb, $4::jsonb, true, NOW(), NOW(), NOW())
                RETURNING *
            """
            
            row = await db.fetch_one(
                query,
                document_id,
                json.dumps([{"id": "brain-default", "name": "Brain Default"}]),
                json.dumps({"provider": "ollama", "model": "llama3.2"}),
                json.dumps({"requests_per_minute": 60, "tokens_per_minute": 100000}),
            )
            
            return ModelConfigRepository._row_to_config(row)
            
        except Exception as e:
            logger.error(f"Error creating model config: {e}")
            raise
    
    @staticmethod
    def _row_to_config(row) -> BrainModelConfig:
        """Convert database row to BrainModelConfig model."""
        available_models = row.get('available_models')
        backend_llm = row.get('backend_llm')
        rate_limits = row.get('rate_limits')
        
        return BrainModelConfig(
            id=row['id'],
            document_id=row.get('document_id'),
            is_enabled=row.get('is_enabled', False),
            base_url=row.get('base_url'),
            default_model=row.get('default_model'),
            available_models=available_models if isinstance(available_models, list) else None,
            backend_llm=backend_llm if isinstance(backend_llm, dict) else None,
            rate_limits=rate_limits if isinstance(rate_limits, dict) else None,
            logging_enabled=row.get('logging_enabled', True),
            created_at=row.get('created_at'),
            updated_at=row.get('updated_at'),
            published_at=row.get('published_at'),
        )
