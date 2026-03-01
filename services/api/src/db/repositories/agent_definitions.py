# ===========================================
# Agent Definitions Repository
# ===========================================

import json
import logging
from typing import Optional, List, Dict, Any
from ..connection import get_db
from ..models import AgentDefinition, AgentVersion

logger = logging.getLogger(__name__)


class AgentDefinitionRepository:
    """Repository for agent_definitions + agent_versions tables."""

    # ---------- agent_definitions CRUD ----------

    @staticmethod
    async def count() -> int:
        db = get_db()
        row = await db.fetch_one("SELECT COUNT(*) AS cnt FROM agent_definitions")
        return row["cnt"] if row else 0

    @staticmethod
    async def get_all() -> List[AgentDefinition]:
        db = get_db()
        rows = await db.fetch_all(
            "SELECT * FROM agent_definitions ORDER BY name"
        )
        return [AgentDefinitionRepository._row_to_def(r) for r in rows]

    @staticmethod
    async def get_all_enabled() -> List[AgentDefinition]:
        db = get_db()
        rows = await db.fetch_all(
            "SELECT * FROM agent_definitions WHERE is_enabled = TRUE ORDER BY name"
        )
        return [AgentDefinitionRepository._row_to_def(r) for r in rows]

    @staticmethod
    async def get_by_agent_id(agent_id: str) -> Optional[AgentDefinition]:
        db = get_db()
        row = await db.fetch_one(
            "SELECT * FROM agent_definitions WHERE agent_id = $1", agent_id
        )
        return AgentDefinitionRepository._row_to_def(row) if row else None

    @staticmethod
    async def get_by_id(def_id: int) -> Optional[AgentDefinition]:
        db = get_db()
        row = await db.fetch_one(
            "SELECT * FROM agent_definitions WHERE id = $1", def_id
        )
        return AgentDefinitionRepository._row_to_def(row) if row else None

    @staticmethod
    async def create(data: Dict[str, Any]) -> AgentDefinition:
        db = get_db()
        skills_json = json.dumps(data.get("skills", []), ensure_ascii=False)
        settings_json = json.dumps(data.get("settings", {}), ensure_ascii=False)
        domain_tools = data.get("domain_tools", [])
        excluded_core_tools = data.get("excluded_core_tools", [])

        row = await db.fetch_one(
            """
            INSERT INTO agent_definitions
                (agent_id, name, description, role, expertise, task_requirements,
                 system_prompt, domain_tools, core_tools_enabled, excluded_core_tools,
                 skills, is_enabled, version, icon, settings, created_at, updated_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::jsonb,$12,$13,$14,$15::jsonb, NOW(), NOW())
            RETURNING *
            """,
            data["agent_id"],
            data["name"],
            data.get("description"),
            data.get("role"),
            data.get("expertise"),
            data.get("task_requirements"),
            data["system_prompt"],
            domain_tools,
            data.get("core_tools_enabled", True),
            excluded_core_tools,
            skills_json,
            data.get("is_enabled", True),
            data.get("version", "1.0.0"),
            data.get("icon"),
            settings_json,
        )
        return AgentDefinitionRepository._row_to_def(row)

    @staticmethod
    async def update(agent_id: str, data: Dict[str, Any]) -> Optional[AgentDefinition]:
        db = get_db()

        existing = await AgentDefinitionRepository.get_by_agent_id(agent_id)
        if not existing:
            return None

        # Save snapshot before update
        await AgentDefinitionRepository.save_version(
            existing.id,
            existing.model_dump(mode="json"),
            changed_by=data.pop("changed_by", None),
            reason=data.pop("change_reason", None),
        )

        set_clauses = []
        params: list = []
        idx = 1

        field_map = {
            "name": "name",
            "description": "description",
            "role": "role",
            "expertise": "expertise",
            "task_requirements": "task_requirements",
            "system_prompt": "system_prompt",
            "core_tools_enabled": "core_tools_enabled",
            "is_enabled": "is_enabled",
            "version": "version",
            "icon": "icon",
        }
        for key, col in field_map.items():
            if key in data:
                set_clauses.append(f"{col} = ${idx}")
                params.append(data[key])
                idx += 1

        if "domain_tools" in data:
            set_clauses.append(f"domain_tools = ${idx}")
            params.append(data["domain_tools"])
            idx += 1

        if "excluded_core_tools" in data:
            set_clauses.append(f"excluded_core_tools = ${idx}")
            params.append(data["excluded_core_tools"])
            idx += 1

        if "skills" in data:
            set_clauses.append(f"skills = ${idx}::jsonb")
            params.append(json.dumps(data["skills"], ensure_ascii=False))
            idx += 1

        if "settings" in data:
            set_clauses.append(f"settings = ${idx}::jsonb")
            params.append(json.dumps(data["settings"], ensure_ascii=False))
            idx += 1

        if not set_clauses:
            return existing

        set_clauses.append(f"updated_at = NOW()")
        params.append(agent_id)

        query = f"""
            UPDATE agent_definitions
            SET {', '.join(set_clauses)}
            WHERE agent_id = ${idx}
            RETURNING *
        """
        row = await db.fetch_one(query, *params)
        return AgentDefinitionRepository._row_to_def(row) if row else None

    @staticmethod
    async def delete(agent_id: str) -> bool:
        db = get_db()
        await db.execute(
            "DELETE FROM agent_definitions WHERE agent_id = $1", agent_id
        )
        return True

    # ---------- agent_versions ----------

    @staticmethod
    async def save_version(
        definition_id: int,
        snapshot: Dict[str, Any],
        changed_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> AgentVersion:
        db = get_db()
        next_num_row = await db.fetch_one(
            """
            SELECT COALESCE(MAX(version_number), 0) + 1 AS next_num
            FROM agent_versions
            WHERE agent_definition_id = $1
            """,
            definition_id,
        )
        next_num = next_num_row["next_num"] if next_num_row else 1

        row = await db.fetch_one(
            """
            INSERT INTO agent_versions
                (agent_definition_id, version_number, snapshot, changed_by, change_reason, created_at)
            VALUES ($1, $2, $3::jsonb, $4, $5, NOW())
            RETURNING *
            """,
            definition_id,
            next_num,
            json.dumps(snapshot, ensure_ascii=False, default=str),
            changed_by,
            reason,
        )
        return AgentDefinitionRepository._row_to_version(row)

    @staticmethod
    async def get_versions(agent_id: str) -> List[AgentVersion]:
        db = get_db()
        defn = await AgentDefinitionRepository.get_by_agent_id(agent_id)
        if not defn:
            return []

        rows = await db.fetch_all(
            """
            SELECT * FROM agent_versions
            WHERE agent_definition_id = $1
            ORDER BY version_number DESC
            """,
            defn.id,
        )
        return [AgentDefinitionRepository._row_to_version(r) for r in rows]

    @staticmethod
    async def restore_version(agent_id: str, version_number: int) -> Optional[AgentDefinition]:
        db = get_db()
        defn = await AgentDefinitionRepository.get_by_agent_id(agent_id)
        if not defn:
            return None

        ver_row = await db.fetch_one(
            """
            SELECT * FROM agent_versions
            WHERE agent_definition_id = $1 AND version_number = $2
            """,
            defn.id,
            version_number,
        )
        if not ver_row:
            return None

        snapshot = ver_row["snapshot"]
        if isinstance(snapshot, str):
            snapshot = json.loads(snapshot)

        restore_data = {
            k: snapshot[k]
            for k in (
                "name", "description", "role", "expertise", "task_requirements",
                "system_prompt", "domain_tools", "core_tools_enabled", "skills",
                "is_enabled", "version", "icon", "settings",
            )
            if k in snapshot
        }
        restore_data["change_reason"] = f"Restored from version {version_number}"
        return await AgentDefinitionRepository.update(agent_id, restore_data)

    # ---------- helpers ----------

    @staticmethod
    def _row_to_def(row) -> AgentDefinition:
        skills = row.get("skills", [])
        if isinstance(skills, str):
            try:
                skills = json.loads(skills)
            except (json.JSONDecodeError, TypeError):
                skills = []

        settings = row.get("settings", {})
        if isinstance(settings, str):
            try:
                settings = json.loads(settings)
            except (json.JSONDecodeError, TypeError):
                settings = {}

        domain_tools = row.get("domain_tools", [])
        if domain_tools is None:
            domain_tools = []

        excluded_core_tools = row.get("excluded_core_tools", [])
        if excluded_core_tools is None:
            excluded_core_tools = []

        return AgentDefinition(
            id=row["id"],
            agent_id=row["agent_id"],
            name=row["name"],
            description=row.get("description"),
            role=row.get("role"),
            expertise=row.get("expertise"),
            task_requirements=row.get("task_requirements"),
            system_prompt=row["system_prompt"],
            domain_tools=list(domain_tools),
            core_tools_enabled=row.get("core_tools_enabled", True),
            excluded_core_tools=list(excluded_core_tools),
            skills=skills if isinstance(skills, list) else [],
            is_enabled=row.get("is_enabled", True),
            version=row.get("version", "1.0.0"),
            icon=row.get("icon"),
            settings=settings if isinstance(settings, dict) else {},
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    @staticmethod
    def _row_to_version(row) -> AgentVersion:
        snapshot = row.get("snapshot", {})
        if isinstance(snapshot, str):
            try:
                snapshot = json.loads(snapshot)
            except (json.JSONDecodeError, TypeError):
                snapshot = {}

        return AgentVersion(
            id=row["id"],
            agent_definition_id=row["agent_definition_id"],
            version_number=row["version_number"],
            snapshot=snapshot if isinstance(snapshot, dict) else {},
            changed_by=row.get("changed_by"),
            change_reason=row.get("change_reason"),
            created_at=row.get("created_at"),
        )
