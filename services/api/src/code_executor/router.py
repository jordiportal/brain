"""
Router para el Code Executor y Workspace

Endpoints:
- GET /workspace/files/{path} - Sirve archivos del workspace
- GET /workspace/list/{path} - Lista archivos de un directorio
- DELETE /workspace/files/{path} - Elimina un archivo
"""

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
from typing import Optional
import mimetypes
import io

from .persistent_executor import PersistentCodeExecutor

logger = structlog.get_logger()
router = APIRouter(prefix="/workspace", tags=["Workspace"])

# Instancia del executor
_executor: Optional[PersistentCodeExecutor] = None


def get_executor() -> PersistentCodeExecutor:
    """Obtiene o crea el executor persistente"""
    global _executor
    if _executor is None:
        _executor = PersistentCodeExecutor()
    return _executor


@router.get("/files/{file_path:path}")
async def get_workspace_file(file_path: str):
    """
    Sirve un archivo del workspace del persistent-runner.
    
    Args:
        file_path: Ruta relativa al workspace (ej: media/videos/video.mp4)
    
    Returns:
        El archivo con el Content-Type apropiado
    """
    executor = get_executor()
    
    # Leer el archivo binario
    data = executor.read_binary_file(file_path)
    
    if data is None:
        raise HTTPException(status_code=404, detail=f"Archivo no encontrado: {file_path}")
    
    # Detectar mime type
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None:
        mime_type = "application/octet-stream"
    
    # Nombre del archivo
    filename = Path(file_path).name
    
    logger.info(f"Sirviendo archivo: {file_path} ({len(data)} bytes, {mime_type})")
    
    return StreamingResponse(
        io.BytesIO(data),
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Content-Length": str(len(data))
        }
    )


@router.get("/list/{dir_path:path}")
async def list_workspace_directory(dir_path: str = ""):
    """
    Lista archivos de un directorio del workspace.
    
    Args:
        dir_path: Ruta relativa al workspace (ej: media/videos)
    
    Returns:
        Lista de archivos y directorios
    """
    import subprocess
    
    executor = get_executor()
    full_path = f"{executor.WORKSPACE_PATH}/{dir_path}" if dir_path else executor.WORKSPACE_PATH
    
    try:
        result = subprocess.run(
            ["docker", "exec", executor.CONTAINER_NAME, "ls", "-la", full_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            raise HTTPException(status_code=404, detail=f"Directorio no encontrado: {dir_path}")
        
        # Parsear output de ls -la
        lines = result.stdout.strip().split('\n')
        files = []
        
        for line in lines[1:]:  # Skip "total X" line
            parts = line.split()
            if len(parts) >= 9:
                permissions = parts[0]
                size = int(parts[4]) if parts[4].isdigit() else 0
                name = ' '.join(parts[8:])
                
                if name in ['.', '..']:
                    continue
                
                files.append({
                    "name": name,
                    "is_directory": permissions.startswith('d'),
                    "size": size,
                    "permissions": permissions
                })
        
        return {
            "path": dir_path,
            "files": files
        }
    
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Timeout listando directorio")
    except Exception as e:
        logger.error(f"Error listando directorio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{file_path:path}")
async def delete_workspace_file(file_path: str):
    """
    Elimina un archivo del workspace.
    
    Args:
        file_path: Ruta relativa al workspace
    
    Returns:
        Confirmación de eliminación
    """
    executor = get_executor()
    
    if executor.delete_file(file_path):
        return {"status": "ok", "message": f"Archivo eliminado: {file_path}"}
    else:
        raise HTTPException(status_code=500, detail=f"Error eliminando archivo: {file_path}")


@router.get("/media/recent")
async def list_recent_media(limit: int = 20):
    """
    Lista los archivos multimedia más recientes (imágenes y vídeos).
    
    Args:
        limit: Número máximo de archivos a devolver
    
    Returns:
        Lista de archivos multimedia con URLs
    """
    import subprocess
    
    executor = get_executor()
    
    try:
        # Buscar archivos multimedia ordenados por fecha
        result = subprocess.run(
            [
                "docker", "exec", executor.CONTAINER_NAME,
                "find", f"{executor.WORKSPACE_PATH}/media",
                "-type", "f",
                "-name", "*.mp4", "-o", "-name", "*.webm",
                "-o", "-name", "*.png", "-o", "-name", "*.jpg", "-o", "-name", "*.jpeg",
                "-o", "-name", "*.gif", "-o", "-name", "*.webp"
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            # Directorio no existe aún
            return {"files": []}
        
        files = []
        for line in result.stdout.strip().split('\n'):
            if line:
                # Convertir path absoluto a relativo
                rel_path = line.replace(f"{executor.WORKSPACE_PATH}/", "")
                filename = Path(line).name
                
                # Determinar tipo
                ext = Path(line).suffix.lower()
                media_type = "video" if ext in [".mp4", ".webm"] else "image"
                
                files.append({
                    "path": rel_path,
                    "name": filename,
                    "type": media_type,
                    "url": f"/api/v1/workspace/files/{rel_path}"
                })
        
        return {"files": files[:limit]}
    
    except subprocess.TimeoutExpired:
        return {"files": []}
    except Exception as e:
        logger.error(f"Error listando media: {e}")
        return {"files": []}
