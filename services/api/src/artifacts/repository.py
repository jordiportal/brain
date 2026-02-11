"""
Artefactos - Repositorio para acceso a base de datos
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import structlog

from src.db import get_db
from .models import ArtifactCreate, ArtifactUpdate, ArtifactResponse, ArtifactType, ArtifactStatus

logger = structlog.get_logger()


class ArtifactRepository:
    """Repositorio para operaciones CRUD de artefactos"""
    
    @staticmethod
    async def create(artifact_data: ArtifactCreate) -> Optional[ArtifactResponse]:
        """Crea un nuevo artefacto"""
        try:
            db = get_db()
            
            # Generar artifact_id único si no se proporciona
            artifact_id = artifact_data.file_name.replace(' ', '_').replace('.', '_')
            artifact_id = f"{artifact_data.type.value}_{artifact_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            query = """
                INSERT INTO artifacts (
                    artifact_id, type, title, description, file_path, file_name,
                    mime_type, file_size, conversation_id, agent_id,
                    source, tool_id, metadata, parent_artifact_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13::jsonb, $14)
                RETURNING *
            """
            
            # Serializar metadata a JSON string para PostgreSQL JSONB
            metadata_json = json.dumps(artifact_data.metadata) if artifact_data.metadata else '{}'
            
            row = await db.fetch_one(
                query,
                artifact_id,
                artifact_data.type.value,
                artifact_data.title,
                artifact_data.description,
                artifact_data.file_path,
                artifact_data.file_name,
                artifact_data.mime_type,
                artifact_data.file_size,
                artifact_data.conversation_id,
                artifact_data.agent_id,
                artifact_data.source.value,
                artifact_data.tool_id,
                metadata_json,
                artifact_data.parent_artifact_id
            )
            
            if row:
                logger.info(f"✅ Artifact created: {artifact_id}", type=artifact_data.type.value)
                return ArtifactRepository._row_to_response(row)
            return None
            
        except Exception as e:
            logger.error(f"Error creating artifact: {e}")
            return None
    
    @staticmethod
    async def get_by_id(artifact_id: str) -> Optional[ArtifactResponse]:
        """Obtiene un artefacto por su ID único"""
        try:
            db = get_db()
            
            # Actualizar accessed_at
            await db.execute(
                "UPDATE artifacts SET accessed_at = NOW() WHERE artifact_id = $1",
                artifact_id
            )
            
            query = "SELECT * FROM artifacts WHERE artifact_id = $1 AND status = 'active'"
            row = await db.fetch_one(query, artifact_id)
            
            if row:
                return ArtifactRepository._row_to_response(row)
            return None
            
        except Exception as e:
            logger.error(f"Error getting artifact {artifact_id}: {e}")
            return None
    
    @staticmethod
    async def get_by_db_id(db_id: int) -> Optional[ArtifactResponse]:
        """Obtiene un artefacto por su ID de base de datos"""
        try:
            db = get_db()
            
            await db.execute(
                "UPDATE artifacts SET accessed_at = NOW() WHERE id = $1",
                db_id
            )
            
            query = "SELECT * FROM artifacts WHERE id = $1 AND status = 'active'"
            row = await db.fetch_one(query, db_id)
            
            if row:
                return ArtifactRepository._row_to_response(row)
            return None
            
        except Exception as e:
            logger.error(f"Error getting artifact by db id {db_id}: {e}")
            return None
    
    @staticmethod
    async def list_artifacts(
        conversation_id: Optional[str] = None,
        artifact_type: Optional[ArtifactType] = None,
        agent_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ArtifactResponse]:
        """Lista artefactos con filtros opcionales"""
        try:
            db = get_db()
            
            conditions = ["status = 'active'"]
            params = []
            param_idx = 1
            
            if conversation_id:
                conditions.append(f"conversation_id = ${param_idx}")
                params.append(conversation_id)
                param_idx += 1
            
            if artifact_type:
                conditions.append(f"type = ${param_idx}")
                params.append(artifact_type.value)
                param_idx += 1
            
            if agent_id:
                conditions.append(f"agent_id = ${param_idx}")
                params.append(agent_id)
                param_idx += 1
            
            where_clause = " AND ".join(conditions)
            
            query = f"""
                SELECT * FROM artifacts 
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_idx} OFFSET ${param_idx + 1}
            """
            params.extend([limit, offset])
            
            rows = await db.fetch_all(query, *params)
            return [ArtifactRepository._row_to_response(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error listing artifacts: {e}")
            return []
    
    @staticmethod
    async def count_artifacts(
        conversation_id: Optional[str] = None,
        artifact_type: Optional[ArtifactType] = None
    ) -> int:
        """Cuenta artefactos con filtros"""
        try:
            db = get_db()
            
            conditions = ["status = 'active'"]
            params = []
            param_idx = 1
            
            if conversation_id:
                conditions.append(f"conversation_id = ${param_idx}")
                params.append(conversation_id)
                param_idx += 1
            
            if artifact_type:
                conditions.append(f"type = ${param_idx}")
                params.append(artifact_type.value)
                param_idx += 1
            
            where_clause = " AND ".join(conditions)
            query = f"SELECT COUNT(*) as count FROM artifacts WHERE {where_clause}"
            
            row = await db.fetch_one(query, *params)
            return row.get('count', 0) if row else 0
            
        except Exception as e:
            logger.error(f"Error counting artifacts: {e}")
            return 0
    
    @staticmethod
    async def update(artifact_id: str, update_data: ArtifactUpdate) -> Optional[ArtifactResponse]:
        """Actualiza un artefacto"""
        try:
            db = get_db()
            
            updates = []
            params = []
            param_idx = 1
            
            if update_data.title is not None:
                updates.append(f"title = ${param_idx}")
                params.append(update_data.title)
                param_idx += 1
            
            if update_data.description is not None:
                updates.append(f"description = ${param_idx}")
                params.append(update_data.description)
                param_idx += 1
            
            if update_data.status is not None:
                updates.append(f"status = ${param_idx}")
                params.append(update_data.status.value)
                param_idx += 1
            
            if update_data.metadata is not None:
                updates.append(f"metadata = ${param_idx}::jsonb")
                params.append(json.dumps(update_data.metadata))
                param_idx += 1
            
            if not updates:
                return await ArtifactRepository.get_by_id(artifact_id)
            
            updates.append(f"updated_at = NOW()")
            
            query = f"""
                UPDATE artifacts 
                SET {', '.join(updates)}
                WHERE artifact_id = ${param_idx}
                RETURNING *
            """
            params.append(artifact_id)
            
            row = await db.fetch_one(query, *params)
            
            if row:
                logger.info(f"✅ Artifact updated: {artifact_id}")
                return ArtifactRepository._row_to_response(row)
            return None
            
        except Exception as e:
            logger.error(f"Error updating artifact {artifact_id}: {e}")
            return None
    
    @staticmethod
    async def delete(artifact_id: str, soft_delete: bool = True) -> bool:
        """Elimina un artefacto (soft o hard delete)"""
        try:
            db = get_db()
            
            if soft_delete:
                query = """
                    UPDATE artifacts 
                    SET status = 'deleted', updated_at = NOW()
                    WHERE artifact_id = $1
                """
            else:
                query = "DELETE FROM artifacts WHERE artifact_id = $1"
            
            await db.execute(query, artifact_id)
            logger.info(f"✅ Artifact deleted: {artifact_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting artifact {artifact_id}: {e}")
            return False
    
    @staticmethod
    async def get_recent(limit: int = 20) -> List[ArtifactResponse]:
        """Obtiene los artefactos más recientes"""
        return await ArtifactRepository.list_artifacts(limit=limit, offset=0)
    
    @staticmethod
    def _row_to_response(row) -> ArtifactResponse:
        """Convierte una fila de BD a ArtifactResponse"""
        # Parsear metadata si viene como string JSON
        metadata = row.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        
        return ArtifactResponse(
            id=row['id'],
            artifact_id=row['artifact_id'],
            type=row['type'],
            title=row.get('title'),
            description=row.get('description'),
            file_name=row['file_name'],
            file_path=row['file_path'],
            mime_type=row.get('mime_type'),
            file_size=row.get('file_size'),
            conversation_id=row.get('conversation_id'),
            agent_id=row.get('agent_id'),
            source=row['source'],
            tool_id=row.get('tool_id'),
            metadata=metadata,
            parent_artifact_id=row.get('parent_artifact_id'),
            version=row.get('version', 1),
            is_latest=row.get('is_latest', True),
            status=row['status'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            accessed_at=row['accessed_at']
        )
