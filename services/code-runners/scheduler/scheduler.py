"""
Scheduler de tareas programadas (User Sandbox).
Proceso standalone arrancado por supervisord en el persistent-runner.
Itera sobre directorios de workspace de usuarios, lee user_tasks activas
de cada SQLite (brain_data.db), y las sincroniza con APScheduler.
PostgreSQL se mantiene solo para datos compartidos (user_profiles).
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite
import asyncpg
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("scheduler")

DATABASE_URL = os.environ.get("DATABASE_URL", "")
WORKSPACES_BASE = os.environ.get("WORKSPACES_BASE", "/workspaces")
DB_FILENAME = "brain_data.db"
SYNC_INTERVAL = 60

_pg_pool: asyncpg.Pool | None = None
_scheduler: AsyncIOScheduler | None = None
_active_jobs: set[str] = set()


async def get_pg_pool() -> asyncpg.Pool:
    """PostgreSQL pool for shared data (user_profiles)."""
    global _pg_pool
    if _pg_pool is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL not set")
        _pg_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=3, command_timeout=30)
    return _pg_pool


async def _open_user_db(db_path: str) -> aiosqlite.Connection:
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    await conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _discover_user_dbs() -> list[tuple[str, str]]:
    """Return list of (user_dir_name, db_path) for all users with a brain_data.db."""
    base = Path(WORKSPACES_BASE)
    if not base.is_dir():
        return []
    result = []
    for child in base.iterdir():
        if child.is_dir():
            db_path = child / DB_FILENAME
            if db_path.exists():
                result.append((child.name, str(db_path)))
    return result


async def _process_run_now() -> None:
    """Execute run-now requests from all user SQLite databases."""
    for user_dir, db_path in _discover_user_dbs():
        try:
            conn = await _open_user_db(db_path)
            try:
                async with conn.execute(
                    "SELECT rn.task_id, t.type, t.name "
                    "FROM user_task_run_now rn JOIN user_tasks t ON t.id = rn.task_id"
                ) as cur:
                    rows = await cur.fetchall()
                for r in rows:
                    tid = int(r["task_id"])
                    logger.info("Run-now: task %s (%s) [user_dir=%s]", tid, r["type"], user_dir)
                    await _execute_task(tid, user_dir, db_path, r["type"], r["name"])
                    await conn.execute("DELETE FROM user_task_run_now WHERE task_id = ?", (tid,))
                    await conn.commit()
            finally:
                await conn.close()
        except Exception:
            logger.exception("Error processing run-now for %s", user_dir)


async def sync_tasks() -> None:
    """Sync active user_tasks from all per-user SQLite databases into APScheduler."""
    global _active_jobs
    if not _scheduler:
        return
    try:
        await _process_run_now()
    except Exception:
        logger.exception("Error in run-now phase")

    current: set[str] = set()

    for user_dir, db_path in _discover_user_dbs():
        try:
            conn = await _open_user_db(db_path)
            try:
                async with conn.execute(
                    "SELECT id, type, name, cron_expression FROM user_tasks WHERE is_active = 1"
                ) as cur:
                    rows = await cur.fetchall()
            finally:
                await conn.close()

            for r in rows:
                jid = f"{user_dir}:{r['id']}"
                current.add(jid)
                parts = r["cron_expression"].strip().split()
                if len(parts) != 5:
                    logger.warning("Invalid cron '%s' for task %s/%s", r["cron_expression"], user_dir, r["id"])
                    continue
                try:
                    trigger = CronTrigger(
                        minute=parts[0], hour=parts[1], day=parts[2],
                        month=parts[3], day_of_week=parts[4],
                    )
                    if jid in _active_jobs:
                        _scheduler.reschedule_job(jid, trigger=trigger)
                    else:
                        _scheduler.add_job(
                            _execute_task, trigger=trigger, id=jid, max_instances=1,
                            args=[r["id"], user_dir, db_path, r["type"], r["name"]],
                            replace_existing=True,
                        )
                        _active_jobs.add(jid)
                except Exception:
                    logger.exception("Failed to schedule task %s/%s", user_dir, r["id"])
        except Exception:
            logger.exception("Error syncing tasks for %s", user_dir)

    for jid in list(_active_jobs - current):
        try:
            _scheduler.remove_job(jid)
        except Exception:
            pass
        _active_jobs.discard(jid)


async def _execute_task(task_id: int, user_dir: str, db_path: str, task_type: str, name: str) -> None:
    from executors import get_executor

    executor_fn = get_executor(task_type)
    if not executor_fn:
        logger.warning("No executor for type '%s'", task_type)
        await _update_status(db_path, task_id, "error")
        return
    try:
        await _update_status(db_path, task_id, "running")
        await executor_fn(db_path, task_id, user_dir, name)
        await _update_status(db_path, task_id, "success")
    except Exception:
        logger.exception("Task %s/%s failed", user_dir, task_id)
        await _update_status(db_path, task_id, "error")


async def _update_status(db_path: str, task_id: int, status: str) -> None:
    conn = await _open_user_db(db_path)
    try:
        await conn.execute(
            "UPDATE user_tasks SET last_run_at = ?, last_status = ?, updated_at = datetime('now') WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), status, task_id),
        )
        await conn.commit()
    finally:
        await conn.close()


async def main() -> None:
    global _scheduler
    base = Path(WORKSPACES_BASE)
    if not base.is_dir():
        logger.error("WORKSPACES_BASE %s does not exist — exiting", WORKSPACES_BASE)
        return
    if DATABASE_URL:
        await get_pg_pool()
        logger.info("PostgreSQL pool ready (for user_profiles)")
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(sync_tasks, "interval", seconds=SYNC_INTERVAL, id="_sync")
    _scheduler.start()
    await sync_tasks()
    user_count = len(_discover_user_dbs())
    logger.info("Scheduler running (sync every %ss, %d user DBs found)", SYNC_INTERVAL, user_count)
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
