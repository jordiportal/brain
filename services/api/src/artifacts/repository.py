"""
Artefactos - Repositorio per-user SQLite
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import structlog

from src.db.user_db import user_db, row_to_dict
from .models import ArtifactCreate, ArtifactUpdate, ArtifactResponse, ArtifactType, ArtifactStatus

logger = structlog.get_logger()


class ArtifactRepository:

    @staticmethod
    async def create(user_id: str, artifact_data: ArtifactCreate) -> Optional[ArtifactResponse]:
        try:
            conn = await user_db.get_connection(user_id)

            artifact_id = artifact_data.file_name.replace(' ', '_').replace('.', '_')
            artifact_id = f"{artifact_data.type.value}_{artifact_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            metadata_json = json.dumps(artifact_data.metadata) if artifact_data.metadata else '{}'

            async with conn.execute(
                """
                INSERT INTO artifacts (
                    artifact_id, type, title, description, file_path, file_name,
                    mime_type, file_size, conversation_id, agent_id,
                    source, tool_id, metadata, parent_artifact_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
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
                    artifact_data.parent_artifact_id,
                ),
            ) as cur:
                last_id = cur.lastrowid
            await conn.commit()

            return await ArtifactRepository.get_by_db_id(user_id, last_id)  # type: ignore[arg-type]

        except Exception as e:
            logger.error(f"Error creating artifact: {e}")
            return None

    @staticmethod
    async def get_by_id(user_id: str, artifact_id: str) -> Optional[ArtifactResponse]:
        try:
            conn = await user_db.get_connection(user_id)

            await conn.execute(
                "UPDATE artifacts SET accessed_at = datetime('now') WHERE artifact_id = ?",
                (artifact_id,),
            )
            await conn.commit()

            async with conn.execute(
                "SELECT * FROM artifacts WHERE artifact_id = ? AND status = 'active'",
                (artifact_id,),
            ) as cur:
                row = await cur.fetchone()

            return ArtifactRepository._row_to_response(row_to_dict(row)) if row else None

        except Exception as e:
            logger.error(f"Error getting artifact {artifact_id}: {e}")
            return None

    @staticmethod
    async def get_by_db_id(user_id: str, db_id: int) -> Optional[ArtifactResponse]:
        try:
            conn = await user_db.get_connection(user_id)

            await conn.execute(
                "UPDATE artifacts SET accessed_at = datetime('now') WHERE id = ?",
                (db_id,),
            )
            await conn.commit()

            async with conn.execute(
                "SELECT * FROM artifacts WHERE id = ? AND status = 'active'",
                (db_id,),
            ) as cur:
                row = await cur.fetchone()

            return ArtifactRepository._row_to_response(row_to_dict(row)) if row else None

        except Exception as e:
            logger.error(f"Error getting artifact by db id {db_id}: {e}")
            return None

    @staticmethod
    async def list_artifacts(
        user_id: str,
        conversation_id: Optional[str] = None,
        artifact_type: Optional[ArtifactType] = None,
        agent_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ArtifactResponse]:
        try:
            conn = await user_db.get_connection(user_id)

            conditions = ["status = 'active'"]
            params: list[Any] = []

            if conversation_id:
                conditions.append("conversation_id = ?")
                params.append(conversation_id)
            if artifact_type:
                conditions.append("type = ?")
                params.append(artifact_type.value)
            if agent_id:
                conditions.append("agent_id = ?")
                params.append(agent_id)

            where_clause = " AND ".join(conditions)
            params.extend([limit, offset])

            async with conn.execute(
                f"SELECT * FROM artifacts WHERE {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                params,
            ) as cur:
                rows = await cur.fetchall()
            return [ArtifactRepository._row_to_response(row_to_dict(r)) for r in rows]

        except Exception as e:
            logger.error(f"Error listing artifacts: {e}")
            return []

    @staticmethod
    async def count_artifacts(
        user_id: str,
        conversation_id: Optional[str] = None,
        artifact_type: Optional[ArtifactType] = None,
    ) -> int:
        try:
            conn = await user_db.get_connection(user_id)

            conditions = ["status = 'active'"]
            params: list[Any] = []

            if conversation_id:
                conditions.append("conversation_id = ?")
                params.append(conversation_id)
            if artifact_type:
                conditions.append("type = ?")
                params.append(artifact_type.value)

            where_clause = " AND ".join(conditions)

            async with conn.execute(
                f"SELECT COUNT(*) as count FROM artifacts WHERE {where_clause}",
                params,
            ) as cur:
                row = await cur.fetchone()
            return dict(row).get("count", 0) if row else 0

        except Exception as e:
            logger.error(f"Error counting artifacts: {e}")
            return 0

    @staticmethod
    async def update(user_id: str, artifact_id: str, update_data: ArtifactUpdate) -> Optional[ArtifactResponse]:
        try:
            conn = await user_db.get_connection(user_id)

            updates: list[str] = []
            params: list[Any] = []

            if update_data.title is not None:
                updates.append("title = ?")
                params.append(update_data.title)
            if update_data.description is not None:
                updates.append("description = ?")
                params.append(update_data.description)
            if update_data.status is not None:
                updates.append("status = ?")
                params.append(update_data.status.value)
            if update_data.metadata is not None:
                updates.append("metadata = ?")
                params.append(json.dumps(update_data.metadata))

            if not updates:
                return await ArtifactRepository.get_by_id(user_id, artifact_id)

            updates.append("updated_at = datetime('now')")
            params.append(artifact_id)

            await conn.execute(
                f"UPDATE artifacts SET {', '.join(updates)} WHERE artifact_id = ?",
                params,
            )
            await conn.commit()
            return await ArtifactRepository.get_by_id(user_id, artifact_id)

        except Exception as e:
            logger.error(f"Error updating artifact {artifact_id}: {e}")
            return None

    @staticmethod
    async def delete(user_id: str, artifact_id: str, soft_delete: bool = True) -> bool:
        try:
            conn = await user_db.get_connection(user_id)

            if soft_delete:
                await conn.execute(
                    "UPDATE artifacts SET status = 'deleted', updated_at = datetime('now') WHERE artifact_id = ?",
                    (artifact_id,),
                )
            else:
                await conn.execute("DELETE FROM artifacts WHERE artifact_id = ?", (artifact_id,))
            await conn.commit()
            logger.info(f"Artifact deleted: {artifact_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting artifact {artifact_id}: {e}")
            return False

    @staticmethod
    async def get_recent(user_id: str, limit: int = 20) -> List[ArtifactResponse]:
        return await ArtifactRepository.list_artifacts(user_id, limit=limit, offset=0)

    @staticmethod
    def _row_to_response(d: dict) -> ArtifactResponse:
        metadata = d.get("metadata", {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}

        created_at = d.get("created_at") or datetime.now().isoformat()
        updated_at = d.get("updated_at") or created_at
        accessed_at = d.get("accessed_at") or created_at

        return ArtifactResponse(
            id=d["id"],
            artifact_id=d["artifact_id"],
            type=d["type"],
            title=d.get("title"),
            description=d.get("description"),
            file_name=d["file_name"],
            file_path=d["file_path"],
            mime_type=d.get("mime_type"),
            file_size=d.get("file_size"),
            conversation_id=d.get("conversation_id"),
            agent_id=d.get("agent_id"),
            source=d["source"],
            tool_id=d.get("tool_id"),
            metadata=metadata,
            parent_artifact_id=d.get("parent_artifact_id"),
            version=d.get("version", 1),
            is_latest=bool(d.get("is_latest", True)),
            status=d["status"],
            created_at=created_at,
            updated_at=updated_at,
            accessed_at=accessed_at,
        )
