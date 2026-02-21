"""
Scheduler de tareas programadas (User Sandbox).
Proceso standalone arrancado por supervisord en el persistent-runner.
Lee user_tasks activas de PostgreSQL y las sincroniza con APScheduler cada 60s.
También procesa solicitudes de ejecución inmediata (user_task_run_now).
"""

import asyncio
import logging
import os
from datetime import datetime, timezone

import asyncpg
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("scheduler")

DATABASE_URL = os.environ.get("DATABASE_URL", "")
SYNC_INTERVAL = 60

_pool: asyncpg.Pool | None = None
_scheduler: AsyncIOScheduler | None = None
_active_jobs: set[str] = set()


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL not set")
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=3, command_timeout=30)
    return _pool


async def _process_run_now() -> None:
    """Ejecuta tareas con solicitud run-now pendiente."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT rn.task_id, t.user_id, t.type, t.name "
            "FROM user_task_run_now rn JOIN user_tasks t ON t.id = rn.task_id "
            "ORDER BY rn.requested_at"
        )
    for r in rows:
        tid = int(r["task_id"])
        logger.info("Run-now: task %s (%s)", tid, r["type"])
        await _execute_task(tid, r["user_id"], r["type"], r["name"])
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM user_task_run_now WHERE task_id = $1", tid)


async def sync_tasks() -> None:
    """Sincroniza user_tasks activas con APScheduler y procesa run-now."""
    global _active_jobs
    if not _scheduler:
        return
    try:
        await _process_run_now()
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, user_id, type, name, cron_expression FROM user_tasks WHERE is_active = true"
            )
    except Exception:
        logger.exception("Error syncing tasks")
        return

    current = {str(r["id"]) for r in rows}

    for jid in list(_active_jobs - current):
        try:
            _scheduler.remove_job(jid)
        except Exception:
            pass
        _active_jobs.discard(jid)

    for r in rows:
        jid = str(r["id"])
        parts = r["cron_expression"].strip().split()
        if len(parts) != 5:
            logger.warning("Invalid cron '%s' for task %s", r["cron_expression"], jid)
            continue
        try:
            trigger = CronTrigger(minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4])
            if jid in _active_jobs:
                _scheduler.reschedule_job(jid, trigger=trigger)
            else:
                _scheduler.add_job(
                    _execute_task, trigger=trigger, id=jid, max_instances=1,
                    args=[r["id"], r["user_id"], r["type"], r["name"]],
                    replace_existing=True,
                )
                _active_jobs.add(jid)
        except Exception:
            logger.exception("Failed to schedule task %s", jid)


async def _execute_task(task_id: int, user_id: str, task_type: str, name: str) -> None:
    from executors import get_executor

    pool = await get_pool()
    executor_fn = get_executor(task_type)
    if not executor_fn:
        logger.warning("No executor for type '%s'", task_type)
        await _update_status(pool, task_id, "error")
        return
    try:
        await _update_status(pool, task_id, "running")
        await executor_fn(pool, task_id, user_id, name)
        await _update_status(pool, task_id, "success")
    except Exception:
        logger.exception("Task %s failed", task_id)
        await _update_status(pool, task_id, "error")


async def _update_status(pool: asyncpg.Pool, task_id: int, status: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE user_tasks SET last_run_at = $1, last_status = $2, updated_at = NOW() WHERE id = $3",
            datetime.now(timezone.utc), status, task_id,
        )


async def main() -> None:
    global _scheduler
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set — exiting")
        return
    await get_pool()
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(sync_tasks, "interval", seconds=SYNC_INTERVAL, id="_sync")
    _scheduler.start()
    await sync_tasks()
    logger.info("Scheduler running (sync every %ss)", SYNC_INTERVAL)
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
