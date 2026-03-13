"""
SkillSyncService — synchronises skills from a Git repository to the database.

Flow:
  1. Clone or pull the configured Git repo
  2. Parse all SKILL.md files + agents.yaml
  3. Upsert skills into agent_definitions.skills (JSONB)
  4. Hot-reload the subagent registry
"""

import asyncio
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog

from .parser import ParsedSkill, discover_skills, parse_agents_yaml

logger = structlog.get_logger(__name__)


@dataclass
class SyncStatus:
    last_sync: Optional[datetime] = None
    last_commit: str = ""
    branch: str = ""
    repo_url: str = ""
    skills_synced: int = 0
    agents_updated: int = 0
    errors: list[str] = field(default_factory=list)
    in_progress: bool = False
    duration_ms: int = 0


class SkillSyncService:
    """Manages Git clone/pull and DB upsert for external skills."""

    def __init__(self):
        self.repo_url: str = os.getenv("SKILLS_REPO_URL", "")
        self.branch: str = os.getenv("SKILLS_REPO_BRANCH", "main")
        self.token: str = os.getenv("SKILLS_REPO_TOKEN", "")
        self.local_path: Path = Path(
            os.getenv("SKILLS_LOCAL_PATH", "/tmp/brain-skills")
        )
        self.sync_on_startup: bool = (
            os.getenv("SKILLS_SYNC_ON_STARTUP", "true").lower() == "true"
        )
        self.sync_interval: int = int(
            os.getenv("SKILLS_SYNC_INTERVAL_MINUTES", "0")
        )
        self.status = SyncStatus(repo_url=self.repo_url, branch=self.branch)
        self._bg_task: Optional[asyncio.Task] = None

    @property
    def is_configured(self) -> bool:
        return bool(self.repo_url)

    def _auth_url(self) -> str:
        """Inject token into HTTPS URL if provided."""
        url = self.repo_url
        if self.token and url.startswith("https://"):
            url = url.replace("https://", f"https://x-access-token:{self.token}@", 1)
        return url

    def _git(self, *args: str, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        return subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=cwd or self.local_path,
            env=env,
        )

    def _clone_or_pull(self) -> str:
        """Clone the repo (first time) or pull (subsequent). Returns HEAD commit hash."""
        if (self.local_path / ".git").is_dir():
            self._git("fetch", "origin", self.branch)
            self._git("checkout", self.branch)
            self._git("reset", "--hard", f"origin/{self.branch}")
        else:
            self.local_path.mkdir(parents=True, exist_ok=True)
            result = self._git(
                "clone",
                "--branch", self.branch,
                "--depth", "1",
                self._auth_url(),
                str(self.local_path),
                cwd=self.local_path.parent,
            )
            if result.returncode != 0:
                raise RuntimeError(f"git clone failed: {result.stderr.strip()}")

        rev = self._git("rev-parse", "--short", "HEAD")
        return rev.stdout.strip()

    async def sync(self) -> SyncStatus:
        """Run a full sync: pull repo, parse skills, upsert to DB, hot-reload."""
        if not self.is_configured:
            self.status.errors = ["SKILLS_REPO_URL not configured"]
            return self.status

        if self.status.in_progress:
            return self.status

        self.status.in_progress = True
        self.status.errors = []
        start = time.monotonic()

        try:
            commit = await asyncio.to_thread(self._clone_or_pull)
            self.status.last_commit = commit
            self.status.branch = self.branch
            logger.info("Skills repo updated", commit=commit, branch=self.branch)

            skills = await asyncio.to_thread(discover_skills, self.local_path)
            agent_map = await asyncio.to_thread(
                parse_agents_yaml, self.local_path / "agents.yaml"
            )

            agents_updated = await self._upsert_skills(skills, agent_map)

            try:
                await self._reload_subagents()
            except Exception as exc:
                self.status.errors.append(f"Hot-reload failed: {exc}")
                logger.warning("Subagent hot-reload failed after sync", error=str(exc))

            self.status.skills_synced = len(skills)
            self.status.agents_updated = agents_updated
            self.status.last_sync = datetime.now(timezone.utc)
            self.status.duration_ms = int((time.monotonic() - start) * 1000)

            logger.info(
                "Skills sync complete",
                skills=len(skills),
                agents=agents_updated,
                duration_ms=self.status.duration_ms,
            )

        except Exception as exc:
            self.status.errors.append(str(exc))
            logger.error("Skills sync failed", error=str(exc))
        finally:
            self.status.in_progress = False

        return self.status

    async def _upsert_skills(
        self,
        skills: list[ParsedSkill],
        agent_map: dict[str, list[str]],
    ) -> int:
        """Upsert parsed skills into agent_definitions.skills JSONB column."""
        from src.db.repositories.agent_definitions import AgentDefinitionRepository

        agent_to_skills: dict[str, list[dict]] = {}
        for agent_id, skill_names in agent_map.items():
            agent_to_skills[agent_id] = []
            for sname in skill_names:
                matching = [s for s in skills if s.name == sname]
                if matching:
                    sk = matching[0]
                    agent_to_skills[agent_id].append({
                        "id": sk.brain_id,
                        "name": sk.display_name or sk.name,
                        "description": sk.description,
                        "content": sk.content,
                        "source": "git",
                    })
                else:
                    self.status.errors.append(
                        f"Skill '{sname}' listed for agent '{agent_id}' not found"
                    )

        updated = 0
        for agent_id, skill_list in agent_to_skills.items():
            if not skill_list:
                continue
            existing = await AgentDefinitionRepository.get_by_agent_id(agent_id)
            if not existing:
                logger.warning("Agent not found in DB, skipping", agent_id=agent_id)
                continue

            current_skills = existing.skills or []
            git_ids = {s["id"] for s in skill_list}
            local_skills = [
                s for s in current_skills
                if s.get("id") not in git_ids and s.get("source") != "git"
            ]
            merged = skill_list + local_skills

            await AgentDefinitionRepository.update(
                agent_id,
                {"skills": merged, "changed_by": "skills-sync", "change_reason": f"Git sync ({self.status.last_commit})"},
            )
            updated += 1

        return updated

    async def _reload_subagents(self):
        from src.engine.chains.agents.base import reload_subagents
        await reload_subagents()

    async def start_background_sync(self):
        """Start periodic background sync if configured."""
        if not self.is_configured:
            logger.info("Skills sync disabled: SKILLS_REPO_URL not set")
            return

        if self.sync_on_startup:
            await self.sync()

        if self.sync_interval > 0:
            self._bg_task = asyncio.create_task(self._periodic_sync())
            logger.info(
                "Skills periodic sync started",
                interval_minutes=self.sync_interval,
            )

    async def _periodic_sync(self):
        while True:
            await asyncio.sleep(self.sync_interval * 60)
            try:
                await self.sync()
            except Exception as exc:
                logger.error("Periodic skills sync error", error=str(exc))

    def stop(self):
        if self._bg_task:
            self._bg_task.cancel()
            self._bg_task = None

    def get_repo_info(self) -> dict:
        """Return configuration info (safe for API responses)."""
        return {
            "configured": self.is_configured,
            "repo_url": self.repo_url,
            "branch": self.branch,
            "local_path": str(self.local_path),
            "sync_on_startup": self.sync_on_startup,
            "sync_interval_minutes": self.sync_interval,
        }


skill_sync_service = SkillSyncService()
