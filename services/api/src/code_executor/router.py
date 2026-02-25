"""
Router para el Code Executor y Workspace

Endpoints (todos aceptan ?user_id para scoping per-user sandbox):
- GET /workspace/files/{path} - Sirve archivos del workspace
- POST /workspace/files/upload - Sube archivo al workspace del usuario
- GET /workspace/list/{path} - Lista archivos de un directorio
- DELETE /workspace/files/{path} - Elimina un archivo
- GET /workspace/media/recent - Lista archivos multimedia recientes
- GET /workspace/sandboxes - Lista sandboxes activos (admin)
"""

import subprocess
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from src.auth import require_role
from pathlib import Path
from typing import Optional
import mimetypes
import io

from .sandbox_manager import sandbox_manager

logger = structlog.get_logger()
router = APIRouter(prefix="/workspace", tags=["Workspace"])

FALLBACK_CONTAINER = "brain-persistent-runner"


async def _get_executor(user_id: Optional[str] = None):
    """Resolve the executor for the given user (or fallback)."""
    if user_id:
        return await sandbox_manager.get_or_create(user_id)
    from .persistent_executor import PersistentCodeExecutor
    return PersistentCodeExecutor(FALLBACK_CONTAINER)


@router.get("/files/{file_path:path}")
async def get_workspace_file(file_path: str, user_id: Optional[str] = Query(None)):
    """Sirve un archivo del workspace del sandbox del usuario."""
    executor = await _get_executor(user_id)

    data = executor.read_binary_file(file_path)

    if data is None:
        raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {file_path}")

    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        mime_type = "application/octet-stream"

    filename = Path(file_path).name
    logger.info("Serving file", path=file_path, size=len(data), mime=mime_type, user=user_id)

    return StreamingResponse(
        io.BytesIO(data),
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Content-Length": str(len(data)),
        },
    )


@router.post("/files/upload")
async def upload_workspace_file(
    file: UploadFile = File(...),
    path: str = Form("uploads"),
    user_id: Optional[str] = Query(None),
):
    """Sube un archivo al workspace del sandbox del usuario."""
    executor = await _get_executor(user_id)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    safe_name = Path(file.filename).name
    target_path = f"{path}/{safe_name}"

    success = executor.write_binary_file(target_path, content)
    if not success:
        raise HTTPException(status_code=500, detail=f"Error guardando archivo: {target_path}")

    logger.info("File uploaded to workspace", path=target_path, size=len(content), user=user_id)

    return {
        "status": "ok",
        "file_name": safe_name,
        "path": target_path,
        "size": len(content),
        "url": f"/api/v1/workspace/files/{target_path}",
    }


@router.get("/list/{dir_path:path}")
async def list_workspace_directory(dir_path: str = "", user_id: Optional[str] = Query(None)):
    """Lista archivos de un directorio del workspace del sandbox del usuario."""
    executor = await _get_executor(user_id)
    full_path = f"{executor.WORKSPACE_PATH}/{dir_path}" if dir_path else executor.WORKSPACE_PATH

    try:
        result = subprocess.run(
            ["docker", "exec", executor.container_name, "ls", "-la", full_path],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            raise HTTPException(status_code=404, detail=f"Directorio no encontrado: {dir_path}")

        lines = result.stdout.strip().split("\n")
        files = []

        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 9:
                permissions = parts[0]
                size = int(parts[4]) if parts[4].isdigit() else 0
                name = " ".join(parts[8:])

                if name in [".", ".."]:
                    continue

                files.append(
                    {
                        "name": name,
                        "is_directory": permissions.startswith("d"),
                        "size": size,
                        "permissions": permissions,
                    }
                )

        return {"path": dir_path, "files": files}

    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Timeout listando directorio")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error listing directory", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_path:path}")
async def delete_workspace_file(file_path: str, user_id: Optional[str] = Query(None)):
    """Elimina un archivo del workspace del sandbox del usuario."""
    executor = await _get_executor(user_id)

    if executor.delete_file(file_path):
        return {"status": "ok", "message": f"Archivo eliminado: {file_path}"}
    else:
        raise HTTPException(status_code=500, detail=f"Error eliminando archivo: {file_path}")


@router.get("/media/recent")
async def list_recent_media(limit: int = 20, user_id: Optional[str] = Query(None)):
    """Lista los archivos multimedia más recientes del sandbox del usuario."""
    executor = await _get_executor(user_id)

    try:
        result = subprocess.run(
            [
                "docker", "exec", executor.container_name,
                "find", f"{executor.WORKSPACE_PATH}/media",
                "-type", "f",
                "-name", "*.mp4", "-o", "-name", "*.webm",
                "-o", "-name", "*.png", "-o", "-name", "*.jpg", "-o", "-name", "*.jpeg",
                "-o", "-name", "*.gif", "-o", "-name", "*.webp",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            return {"files": []}

        files = []
        for line in result.stdout.strip().split("\n"):
            if line:
                rel_path = line.replace(f"{executor.WORKSPACE_PATH}/", "")
                filename = Path(line).name
                ext = Path(line).suffix.lower()
                media_type = "video" if ext in [".mp4", ".webm"] else "image"
                files.append(
                    {
                        "path": rel_path,
                        "name": filename,
                        "type": media_type,
                        "url": f"/api/v1/workspace/files/{rel_path}",
                    }
                )

        return {"files": files[:limit]}

    except subprocess.TimeoutExpired:
        return {"files": []}
    except Exception as e:
        logger.error("Error listing media", error=str(e))
        return {"files": []}


@router.get("/sandboxes", dependencies=[Depends(require_role("admin"))])
async def list_sandboxes():
    """Lista sandboxes con datos de brain_users cruzados."""
    from src.db import get_db
    db = get_db()

    sandboxes = await sandbox_manager.list_sandboxes()

    users = await db.fetch_all(
        "SELECT id, email, firstname, lastname, role, is_active FROM brain_users ORDER BY id"
    )
    users_by_email = {u["email"]: dict(u) for u in users}

    for s in sandboxes:
        u = users_by_email.get(s["user_id"])
        s["user_info"] = u

    users_without_sandbox = []
    sandbox_user_ids = {s["user_id"] for s in sandboxes}
    for u in users:
        if u["email"] not in sandbox_user_ids:
            users_without_sandbox.append(dict(u))

    return {
        "sandboxes": sandboxes,
        "users_without_sandbox": users_without_sandbox,
    }


@router.post("/sandboxes/{user_id:path}", dependencies=[Depends(require_role("admin"))])
async def create_sandbox(user_id: str):
    """Crea un sandbox para un usuario (admin)."""
    try:
        await sandbox_manager.get_or_create(user_id)
        return {"status": "ok", "message": f"Sandbox de {user_id} creado"}
    except Exception as e:
        logger.error("Error creating sandbox", user=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sandboxes/{user_id:path}", dependencies=[Depends(require_role("admin"))])
async def remove_sandbox(user_id: str):
    """Elimina el sandbox de un usuario (admin)."""
    try:
        await sandbox_manager.remove_sandbox(user_id)
        return {"status": "ok", "message": f"Sandbox de {user_id} eliminado"}
    except Exception as e:
        logger.error("Error removing sandbox", user=user_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
