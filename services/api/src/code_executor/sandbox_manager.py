"""
SandboxManager — Per-user Docker container lifecycle management.

Creates, starts, stops and removes isolated sandbox containers per user.
Each sandbox uses the same image as the shared persistent-runner but with
its own volume, env vars and resource limits.
"""

import asyncio
import hashlib
import os
import subprocess
import time
from dataclasses import dataclass
from typing import Dict, Optional

import structlog

from ..db import get_db

logger = structlog.get_logger()

SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "brain-persistent-runner:latest")
SANDBOX_NETWORK = os.getenv("SANDBOX_NETWORK", "brain-network")
WORKSPACE_HOST_BASE = os.getenv("SANDBOX_WORKSPACE_BASE", "/Users/jordip/Docker/workspace/users")

DEFAULT_RESOURCE_LIMITS = {"memory": "256m", "cpus": "0.5"}
FALLBACK_CONTAINER = "brain-persistent-runner"


@dataclass
class SandboxInfo:
    user_id: str
    container_name: str
    status: str
    last_accessed_at: Optional[str] = None


class SandboxManager:
    """Manages per-user Docker sandbox containers."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._access_cache: Dict[str, float] = {}

    @staticmethod
    def _container_name(user_id: str) -> str:
        h = hashlib.sha256(user_id.lower().encode()).hexdigest()[:12]
        return f"brain-sandbox-{h}"

    @staticmethod
    def _host_workspace(user_id: str) -> str:
        safe = user_id.lower().replace("@", "_at_").replace(".", "_")
        return os.path.join(WORKSPACE_HOST_BASE, safe)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_or_create(self, user_id: str) -> "PersistentCodeExecutor":
        """Return a ready executor pointing to the user's sandbox container."""
        from .persistent_executor import PersistentCodeExecutor

        if not user_id:
            return PersistentCodeExecutor(FALLBACK_CONTAINER)

        container_name = self._container_name(user_id)

        async with self._lock:
            db_row = await self._db_get(user_id)

            if db_row is None:
                await self._create_container(user_id, container_name)
            elif db_row["status"] != "running":
                if not self._is_running(container_name):
                    if self._container_exists(container_name):
                        self._start(container_name)
                    else:
                        await self._create_container(user_id, container_name)
                await self._db_set_status(user_id, "running")

            await self._db_touch(user_id)

        self._access_cache[user_id] = time.time()
        return PersistentCodeExecutor(container_name)

    async def stop_idle(self, max_idle_minutes: int = 30) -> int:
        """Stop containers that have been idle longer than max_idle_minutes."""
        db = get_db()
        rows = await db.fetch_all(
            "SELECT user_id, container_name FROM user_sandboxes "
            "WHERE status = 'running' "
            "  AND last_accessed_at < NOW() - ($1 || ' minutes')::interval",
            str(max_idle_minutes),
        )
        stopped = 0
        for r in rows:
            cn = r["container_name"]
            uid = r["user_id"]
            if self._is_running(cn):
                logger.info("Stopping idle sandbox", container=cn, user=uid)
                self._stop(cn)
            await self._db_set_status(uid, "stopped")
            self._access_cache.pop(uid, None)
            stopped += 1
        return stopped

    async def list_sandboxes(self):
        db = get_db()
        rows = await db.fetch_all(
            "SELECT user_id, container_name, status, last_accessed_at, created_at "
            "FROM user_sandboxes ORDER BY last_accessed_at DESC"
        )
        return [dict(r) for r in rows]

    async def remove_sandbox(self, user_id: str) -> bool:
        container_name = self._container_name(user_id)
        if self._is_running(container_name):
            self._stop(container_name)
        if self._container_exists(container_name):
            self._remove(container_name)
        db = get_db()
        await db.execute("DELETE FROM user_sandboxes WHERE user_id = $1", user_id)
        self._access_cache.pop(user_id, None)
        return True

    # ------------------------------------------------------------------
    # Container operations (sync, via subprocess)
    # ------------------------------------------------------------------

    async def _create_container(self, user_id: str, container_name: str) -> None:
        host_ws = self._host_workspace(user_id)
        os.makedirs(host_ws, exist_ok=True)

        db = get_db()
        row = await db.fetch_one(
            "SELECT resource_limits FROM user_sandboxes WHERE user_id = $1", user_id
        )
        limits = DEFAULT_RESOURCE_LIMITS
        if row and row.get("resource_limits"):
            import json
            rl = row["resource_limits"]
            if isinstance(rl, str):
                rl = json.loads(rl)
            limits = {**DEFAULT_RESOURCE_LIMITS, **rl}

        env_vars = {
            "WORKSPACE": "/workspace",
            "USER_ID": user_id,
            "DATABASE_URL": os.getenv("DATABASE_URL", ""),
            "REDIS_URL": os.getenv("REDIS_URL", ""),
            "API_URL": os.getenv("API_URL", "http://api:8000"),
            "PROXY_365_URL": os.getenv("PROXY_365_URL", ""),
            "PROXY_365_API_KEY": os.getenv("PROXY_365_API_KEY", ""),
            "BRAIN_API_KEY": os.getenv("BRAIN_API_KEY", ""),
        }

        if self._container_exists(container_name):
            self._remove(container_name)

        cmd = [
            "docker", "create",
            "--name", container_name,
            "--network", SANDBOX_NETWORK,
            "--restart", "unless-stopped",
            f"--memory={limits.get('memory', '256m')}",
            f"--cpus={limits.get('cpus', '0.5')}",
            "-v", f"{host_ws}:/workspace",
        ]
        for k, v in env_vars.items():
            cmd.extend(["-e", f"{k}={v}"])

        cmd.append(SANDBOX_IMAGE)

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            logger.error("Failed to create sandbox", container=container_name, err=result.stderr)
            raise RuntimeError(f"Cannot create sandbox: {result.stderr[:200]}")

        self._start(container_name)

        await db.execute(
            "INSERT INTO user_sandboxes (user_id, container_name, status) "
            "VALUES ($1, $2, 'running') "
            "ON CONFLICT (user_id) DO UPDATE SET container_name = $2, status = 'running', "
            "  last_accessed_at = NOW(), updated_at = NOW()",
            user_id, container_name,
        )
        logger.info("Sandbox created and started", container=container_name, user=user_id)

    @staticmethod
    def _is_running(container_name: str) -> bool:
        try:
            r = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
                capture_output=True, text=True, timeout=5,
            )
            return r.stdout.strip() == "true"
        except Exception:
            return False

    @staticmethod
    def _container_exists(container_name: str) -> bool:
        try:
            r = subprocess.run(
                ["docker", "inspect", container_name],
                capture_output=True, text=True, timeout=5,
            )
            return r.returncode == 0
        except Exception:
            return False

    @staticmethod
    def _start(container_name: str) -> None:
        subprocess.run(["docker", "start", container_name], capture_output=True, timeout=15)

    @staticmethod
    def _stop(container_name: str) -> None:
        subprocess.run(["docker", "stop", "-t", "10", container_name], capture_output=True, timeout=20)

    @staticmethod
    def _remove(container_name: str) -> None:
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True, timeout=10)

    # ------------------------------------------------------------------
    # Database helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _db_get(user_id: str):
        db = get_db()
        return await db.fetch_one(
            "SELECT user_id, container_name, status FROM user_sandboxes WHERE user_id = $1",
            user_id,
        )

    @staticmethod
    async def _db_set_status(user_id: str, status: str) -> None:
        db = get_db()
        await db.execute(
            "UPDATE user_sandboxes SET status = $1, updated_at = NOW() WHERE user_id = $2",
            status, user_id,
        )

    @staticmethod
    async def _db_touch(user_id: str) -> None:
        db = get_db()
        await db.execute(
            "UPDATE user_sandboxes SET last_accessed_at = NOW() WHERE user_id = $1",
            user_id,
        )


# Global singleton
sandbox_manager = SandboxManager()
