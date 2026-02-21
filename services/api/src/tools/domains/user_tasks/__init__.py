"""
User Tasks Tools - Gestion de tareas programadas del usuario.

Permite al agente crear, modificar, eliminar y ejecutar tareas
programadas (mail_digest, calendar_briefing), asi como consultar
sus resultados.
"""

from typing import Any, Dict, List, Optional

import structlog

from src.db.repositories.user_tasks import UserTaskRepository
from src.db.repositories.user_task_results import UserTaskResultRepository

logger = structlog.get_logger()

DEFAULT_USER_ID = "jordip@khlloreda.com"

VALID_TASK_TYPES = ["mail_digest", "calendar_briefing"]


# ── Handlers ─────────────────────────────────────────────────────

async def user_tasks_list(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Lista todas las tareas programadas del usuario."""
    uid = user_id or DEFAULT_USER_ID
    try:
        tasks = await UserTaskRepository.get_all(uid)
        summary = [
            {
                "id": t["id"],
                "name": t["name"],
                "type": t["type"],
                "cron_expression": t["cron_expression"],
                "is_active": t["is_active"],
                "last_status": t.get("last_status"),
                "last_run_at": str(t["last_run_at"]) if t.get("last_run_at") else None,
                "next_run_at": str(t["next_run_at"]) if t.get("next_run_at") else None,
            }
            for t in tasks
        ]
        return {"success": True, "tasks": summary, "count": len(summary)}
    except Exception as e:
        logger.error("user_tasks_list failed", error=str(e))
        return {"success": False, "error": str(e)}


async def user_tasks_create(
    name: str,
    type: str,
    cron_expression: str,
    config: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Crea una nueva tarea programada."""
    if type not in VALID_TASK_TYPES:
        return {
            "success": False,
            "error": f"Tipo '{type}' no valido. Tipos disponibles: {', '.join(VALID_TASK_TYPES)}",
        }
    uid = user_id or DEFAULT_USER_ID
    try:
        task = await UserTaskRepository.create({
            "user_id": uid,
            "type": type,
            "name": name,
            "cron_expression": cron_expression,
            "is_active": True,
            "config": config or {},
        })
        return {"success": True, "task": task}
    except Exception as e:
        logger.error("user_tasks_create failed", error=str(e))
        return {"success": False, "error": str(e)}


async def user_tasks_update(
    task_id: int,
    name: Optional[str] = None,
    cron_expression: Optional[str] = None,
    is_active: Optional[bool] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Modifica una tarea programada existente."""
    data: Dict[str, Any] = {}
    if name is not None:
        data["name"] = name
    if cron_expression is not None:
        data["cron_expression"] = cron_expression
    if is_active is not None:
        data["is_active"] = is_active
    if config is not None:
        data["config"] = config
    if not data:
        return {"success": False, "error": "No se proporcionaron campos a actualizar."}
    try:
        task = await UserTaskRepository.update(task_id, data)
        if not task:
            return {"success": False, "error": f"Tarea {task_id} no encontrada."}
        return {"success": True, "task": task}
    except Exception as e:
        logger.error("user_tasks_update failed", error=str(e))
        return {"success": False, "error": str(e)}


async def user_tasks_delete(task_id: int) -> Dict[str, Any]:
    """Elimina una tarea programada."""
    try:
        ok = await UserTaskRepository.delete(task_id)
        if not ok:
            return {"success": False, "error": f"Tarea {task_id} no encontrada."}
        return {"success": True, "deleted": True, "task_id": task_id}
    except Exception as e:
        logger.error("user_tasks_delete failed", error=str(e))
        return {"success": False, "error": str(e)}


async def user_tasks_run_now(task_id: int) -> Dict[str, Any]:
    """Solicita la ejecucion inmediata de una tarea."""
    try:
        task = await UserTaskRepository.get(task_id)
        if not task:
            return {"success": False, "error": f"Tarea {task_id} no encontrada."}
        await UserTaskRepository.request_run_now(task_id)
        return {
            "success": True,
            "message": f"Tarea '{task['name']}' encolada para ejecucion inmediata. El resultado estara disponible en breve.",
            "task_id": task_id,
        }
    except Exception as e:
        logger.error("user_tasks_run_now failed", error=str(e))
        return {"success": False, "error": str(e)}


async def user_tasks_results(
    task_id: int,
    limit: int = 5,
) -> Dict[str, Any]:
    """Consulta los ultimos resultados de una tarea."""
    try:
        task = await UserTaskRepository.get(task_id)
        if not task:
            return {"success": False, "error": f"Tarea {task_id} no encontrada."}
        results = await UserTaskResultRepository.get_by_task(task_id, limit=limit)
        summary = [
            {
                "id": r["id"],
                "title": r["title"],
                "content": r["content"][:500] + ("..." if len(r["content"]) > 500 else ""),
                "is_read": r["is_read"],
                "created_at": str(r["created_at"]),
            }
            for r in results
        ]
        return {
            "success": True,
            "task_name": task["name"],
            "results": summary,
            "count": len(summary),
        }
    except Exception as e:
        logger.error("user_tasks_results failed", error=str(e))
        return {"success": False, "error": str(e)}


# ══════════════════════════════════════════════════════════════════
# Tool Definitions
# ══════════════════════════════════════════════════════════════════

USER_TASKS_TOOLS: Dict[str, Any] = {
    "user_tasks_list": {
        "id": "user_tasks_list",
        "name": "user_tasks_list",
        "description": (
            "Lista las tareas programadas del usuario. "
            "Muestra id, nombre, tipo, expresion cron, estado activo/inactivo y ultimo resultado."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
        "handler": user_tasks_list,
    },
    "user_tasks_create": {
        "id": "user_tasks_create",
        "name": "user_tasks_create",
        "description": (
            "Crea una nueva tarea programada. "
            "Tipos disponibles: 'mail_digest' (resumen de correo), 'calendar_briefing' (briefing de agenda). "
            "El horario se define con expresion cron de 5 campos: minuto hora dia mes dia_semana. "
            "Ejemplo: '0 7 * * 1-5' = lunes a viernes a las 7:00."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Nombre descriptivo de la tarea (ej: 'Resumen matutino de correo').",
                },
                "type": {
                    "type": "string",
                    "enum": VALID_TASK_TYPES,
                    "description": "Tipo de tarea: 'mail_digest' o 'calendar_briefing'.",
                },
                "cron_expression": {
                    "type": "string",
                    "description": "Expresion cron de 5 campos (minuto hora dia mes dia_semana). Ej: '0 7 * * 1-5'.",
                },
                "config": {
                    "type": "object",
                    "description": "Configuracion adicional opcional (JSON).",
                },
            },
            "required": ["name", "type", "cron_expression"],
        },
        "handler": user_tasks_create,
    },
    "user_tasks_update": {
        "id": "user_tasks_update",
        "name": "user_tasks_update",
        "description": (
            "Modifica una tarea programada existente. "
            "Puede cambiar nombre, horario (cron), activar/desactivar, o config. "
            "Usa user_tasks_list primero para obtener el task_id."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "ID de la tarea a modificar.",
                },
                "name": {
                    "type": "string",
                    "description": "Nuevo nombre de la tarea.",
                },
                "cron_expression": {
                    "type": "string",
                    "description": "Nueva expresion cron.",
                },
                "is_active": {
                    "type": "boolean",
                    "description": "true para activar, false para desactivar.",
                },
                "config": {
                    "type": "object",
                    "description": "Nueva configuracion (reemplaza la existente).",
                },
            },
            "required": ["task_id"],
        },
        "handler": user_tasks_update,
    },
    "user_tasks_delete": {
        "id": "user_tasks_delete",
        "name": "user_tasks_delete",
        "description": (
            "Elimina una tarea programada permanentemente. "
            "IMPORTANTE: Confirma con el usuario antes de ejecutar esta accion."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "ID de la tarea a eliminar.",
                },
            },
            "required": ["task_id"],
        },
        "handler": user_tasks_delete,
    },
    "user_tasks_run_now": {
        "id": "user_tasks_run_now",
        "name": "user_tasks_run_now",
        "description": (
            "Solicita la ejecucion inmediata de una tarea programada. "
            "La tarea se encola y el resultado estara disponible en breve. "
            "Usa user_tasks_results para consultar el resultado despues."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "ID de la tarea a ejecutar ahora.",
                },
            },
            "required": ["task_id"],
        },
        "handler": user_tasks_run_now,
    },
    "user_tasks_results": {
        "id": "user_tasks_results",
        "name": "user_tasks_results",
        "description": (
            "Consulta los ultimos resultados/ejecuciones de una tarea programada. "
            "Muestra titulo, contenido (resumen), fecha y estado de lectura."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "ID de la tarea cuyos resultados se quieren consultar.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Numero maximo de resultados a devolver (default 5).",
                },
            },
            "required": ["task_id"],
        },
        "handler": user_tasks_results,
    },
}
