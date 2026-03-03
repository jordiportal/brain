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
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from src.auth import require_role, get_current_user_flexible
from pathlib import Path
from typing import Optional, Dict, Any
import mimetypes
import io

from .sandbox_manager import sandbox_manager
from . import onlyoffice as oo

logger = structlog.get_logger()
router = APIRouter(prefix="/workspace", tags=["Workspace"])

FALLBACK_CONTAINER = "brain-persistent-runner"


async def _get_executor(user_id: Optional[str] = None):
    """Resolve the executor for the given user (or fallback)."""
    if user_id:
        return await sandbox_manager.get_or_create(user_id)
    from .persistent_executor import PersistentCodeExecutor
    return PersistentCodeExecutor(FALLBACK_CONTAINER)


def _uid(user: Dict[str, Any]) -> str:
    return user.get("email") or str(user["id"])


@router.get("/files/{file_path:path}")
async def get_workspace_file(file_path: str, user: dict = Depends(get_current_user_flexible)):
    """Sirve un archivo del workspace del sandbox del usuario."""
    user_id = _uid(user)
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
    user: dict = Depends(get_current_user_flexible),
):
    """Sube un archivo al workspace del sandbox del usuario."""
    user_id = _uid(user)
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
async def list_workspace_directory(dir_path: str = "", user: dict = Depends(get_current_user_flexible)):
    """Lista archivos de un directorio del workspace del sandbox del usuario."""
    user_id = _uid(user)
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
async def delete_workspace_file(file_path: str, user: dict = Depends(get_current_user_flexible)):
    """Elimina un archivo del workspace del sandbox del usuario."""
    user_id = _uid(user)
    executor = await _get_executor(user_id)

    if executor.delete_file(file_path):
        return {"status": "ok", "message": f"Archivo eliminado: {file_path}"}
    else:
        raise HTTPException(status_code=500, detail=f"Error eliminando archivo: {file_path}")


@router.post("/mkdir")
async def create_directory(
    request: Request,
    user: dict = Depends(get_current_user_flexible),
):
    """Crea un directorio en el workspace."""
    body = await request.json()
    dir_path = body.get("path", "").strip("/")
    if not dir_path:
        raise HTTPException(status_code=400, detail="Path requerido")

    user_id = _uid(user)
    executor = await _get_executor(user_id)
    full_path = f"{executor.WORKSPACE_PATH}/{dir_path}"

    result = subprocess.run(
        ["docker", "exec", executor.container_name, "mkdir", "-p", full_path],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Error creando directorio: {result.stderr}")

    return {"status": "ok", "path": dir_path}


@router.post("/files/rename")
async def rename_workspace_file(
    request: Request,
    user: dict = Depends(get_current_user_flexible),
):
    """Renombra un archivo o directorio."""
    body = await request.json()
    old_path = body.get("path", "").strip("/")
    new_name = body.get("new_name", "").strip()
    if not old_path or not new_name:
        raise HTTPException(status_code=400, detail="path y new_name requeridos")
    if "/" in new_name:
        raise HTTPException(status_code=400, detail="new_name no puede contener /")

    user_id = _uid(user)
    executor = await _get_executor(user_id)
    parent = str(Path(old_path).parent)
    new_path = f"{parent}/{new_name}" if parent != "." else new_name
    src = f"{executor.WORKSPACE_PATH}/{old_path}"
    dst = f"{executor.WORKSPACE_PATH}/{new_path}"

    result = subprocess.run(
        ["docker", "exec", executor.container_name, "mv", src, dst],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Error renombrando: {result.stderr}")

    return {"status": "ok", "old_path": old_path, "new_path": new_path}


@router.post("/files/move")
async def move_workspace_file(
    request: Request,
    user: dict = Depends(get_current_user_flexible),
):
    """Mueve un archivo o directorio a otro destino."""
    body = await request.json()
    src_path = body.get("path", "").strip("/")
    dest_dir = body.get("destination", "").strip("/")
    if not src_path:
        raise HTTPException(status_code=400, detail="path requerido")

    user_id = _uid(user)
    executor = await _get_executor(user_id)
    src = f"{executor.WORKSPACE_PATH}/{src_path}"
    dst = f"{executor.WORKSPACE_PATH}/{dest_dir}/" if dest_dir else f"{executor.WORKSPACE_PATH}/"

    result = subprocess.run(
        ["docker", "exec", executor.container_name, "mv", src, dst],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Error moviendo: {result.stderr}")

    filename = Path(src_path).name
    new_path = f"{dest_dir}/{filename}" if dest_dir else filename
    return {"status": "ok", "old_path": src_path, "new_path": new_path}


@router.post("/files/copy")
async def copy_workspace_file(
    request: Request,
    user: dict = Depends(get_current_user_flexible),
):
    """Copia un archivo o directorio."""
    body = await request.json()
    src_path = body.get("path", "").strip("/")
    dest_path = body.get("destination", "").strip("/")
    if not src_path or not dest_path:
        raise HTTPException(status_code=400, detail="path y destination requeridos")

    user_id = _uid(user)
    executor = await _get_executor(user_id)
    src = f"{executor.WORKSPACE_PATH}/{src_path}"
    dst = f"{executor.WORKSPACE_PATH}/{dest_path}"

    result = subprocess.run(
        ["docker", "exec", executor.container_name, "cp", "-r", src, dst],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Error copiando: {result.stderr}")

    return {"status": "ok", "source": src_path, "destination": dest_path}


@router.get("/media/recent")
async def list_recent_media(limit: int = 20, user: dict = Depends(get_current_user_flexible)):
    """Lista los archivos multimedia más recientes del sandbox del usuario."""
    user_id = _uid(user)
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


@router.get("/onlyoffice/status")
async def onlyoffice_status():
    """Check if OnlyOffice integration is enabled."""
    return {"enabled": oo.is_enabled(), "public_url": oo.ONLYOFFICE_PUBLIC_URL}


@router.get("/onlyoffice/config/{file_path:path}")
async def onlyoffice_editor_config(file_path: str, request: Request, user: dict = Depends(get_current_user_flexible)):
    """Generate OnlyOffice editor config for a workspace file."""
    if not oo.is_enabled():
        raise HTTPException(status_code=501, detail="OnlyOffice no configurado")

    user_id = _uid(user)
    user_name = user.get("name") or user.get("firstname", "") or user_id
    filename = Path(file_path).name

    if not oo.is_office_file(filename):
        raise HTTPException(status_code=400, detail=f"Tipo de archivo no soportado: {filename}")

    file_token = oo.generate_file_token(user_id, file_path)
    # URL that OnlyOffice server (inside Docker) will use to fetch the file
    api_internal_url = f"http://api:8000/api/v1/workspace/onlyoffice/file/{file_path}?user_id={user_id}&token={file_token}"

    callback_token = oo.generate_file_token(user_id, f"callback:{file_path}")
    callback_url = f"http://api:8000/api/v1/workspace/onlyoffice/callback?user_id={user_id}&file_path={file_path}&token={callback_token}"

    config = oo.generate_editor_config(
        file_path=file_path,
        filename=filename,
        file_url=api_internal_url,
        user_id=user_id,
        user_name=user_name,
        callback_url=callback_url,
        mode="edit",
    )
    return config


@router.get("/onlyoffice/file/{file_path:path}")
async def onlyoffice_serve_file(file_path: str, user_id: str, token: str):
    """Serve a workspace file to OnlyOffice (token-authenticated, no user session)."""
    if not oo.verify_file_token(user_id, file_path, token):
        raise HTTPException(status_code=403, detail="Token inválido o expirado")

    executor = await _get_executor(user_id)
    data = executor.read_binary_file(file_path)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {file_path}")

    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        mime_type = "application/octet-stream"

    return StreamingResponse(
        io.BytesIO(data),
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{Path(file_path).name}"'},
    )


@router.post("/onlyoffice/callback")
async def onlyoffice_callback(request: Request, user_id: str, file_path: str, token: str):
    """Callback from OnlyOffice when a document is saved."""
    if not oo.verify_file_token(user_id, f"callback:{file_path}", token):
        logger.warning("Invalid OnlyOffice callback token", user=user_id, path=file_path)
        return {"error": 0}

    import aiohttp
    data = await request.json()
    status_code = data.get("status", 0)
    logger.info("OnlyOffice callback", status=status_code, user=user_id, path=file_path)

    if status_code in (2, 6):
        download_url = data.get("url")
        if download_url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(download_url) as resp:
                        if resp.status == 200:
                            content = await resp.read()
                            executor = await _get_executor(user_id)
                            executor.write_binary_file(file_path, content)
                            logger.info("Document saved from OnlyOffice", path=file_path, size=len(content))
            except Exception as e:
                logger.error("Error saving document from OnlyOffice", error=str(e))

    return {"error": 0}


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
