"""
Artefactos - API Router
Endpoints REST para gestión de artefactos
"""

from typing import Optional
from pathlib import Path
import mimetypes
import structlog

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse, HTMLResponse

from .models import (
    ArtifactCreate, ArtifactUpdate, ArtifactResponse, 
    ArtifactListResponse, ArtifactContentResponse, ArtifactType
)
from .repository import ArtifactRepository

logger = structlog.get_logger()
router = APIRouter(prefix="/artifacts", tags=["artifacts"])

# Base path para archivos en workspace
WORKSPACE_BASE = Path("/workspace")


@router.post("", response_model=ArtifactResponse)
async def create_artifact(artifact: ArtifactCreate):
    """
    Crea un nuevo artefacto.
    Usado por tools cuando generan archivos (imágenes, videos, etc.)
    """
    result = await ArtifactRepository.create(artifact)
    if not result:
        raise HTTPException(status_code=500, detail="Error creating artifact")
    return result


@router.get("", response_model=ArtifactListResponse)
async def list_artifacts(
    conversation_id: Optional[str] = None,
    type: Optional[ArtifactType] = None,
    agent_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Lista artefactos con filtros opcionales.
    """
    artifacts = await ArtifactRepository.list_artifacts(
        conversation_id=conversation_id,
        artifact_type=type,
        agent_id=agent_id,
        limit=limit,
        offset=offset
    )
    
    total = await ArtifactRepository.count_artifacts(
        conversation_id=conversation_id,
        artifact_type=type
    )
    
    return ArtifactListResponse(
        artifacts=artifacts,
        total=total,
        page=offset // limit + 1,
        page_size=limit
    )


@router.get("/recent", response_model=ArtifactListResponse)
async def get_recent_artifacts(limit: int = Query(20, ge=1, le=50)):
    """
    Obtiene los artefactos más recientes (para sidebar).
    """
    artifacts = await ArtifactRepository.get_recent(limit=limit)
    return ArtifactListResponse(
        artifacts=artifacts,
        total=len(artifacts),
        page=1,
        page_size=limit
    )


@router.get("/conversation/{conversation_id}", response_model=ArtifactListResponse)
async def get_conversation_artifacts(
    conversation_id: str,
    type: Optional[ArtifactType] = None,
    limit: int = Query(50, ge=1, le=100)
):
    """
    Obtiene todos los artefactos de una conversación.
    """
    artifacts = await ArtifactRepository.list_artifacts(
        conversation_id=conversation_id,
        artifact_type=type,
        limit=limit
    )
    
    return ArtifactListResponse(
        artifacts=artifacts,
        total=len(artifacts),
        page=1,
        page_size=limit
    )


@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(artifact_id: str):
    """
    Obtiene metadata de un artefacto por su ID.
    """
    artifact = await ArtifactRepository.get_by_id(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


@router.put("/{artifact_id}", response_model=ArtifactResponse)
async def update_artifact(artifact_id: str, update: ArtifactUpdate):
    """
    Actualiza metadata de un artefacto.
    """
    result = await ArtifactRepository.update(artifact_id, update)
    if not result:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return result


@router.delete("/{artifact_id}")
async def delete_artifact(artifact_id: str, soft: bool = Query(True)):
    """
    Elimina un artefacto.
    Por defecto hace soft delete (marca como eliminado).
    """
    success = await ArtifactRepository.delete(artifact_id, soft_delete=soft)
    if not success:
        raise HTTPException(status_code=500, detail="Error deleting artifact")
    return {"status": "ok", "message": "Artifact deleted"}


@router.get("/{artifact_id}/content")
async def get_artifact_content(artifact_id: str):
    """
    Obtiene el contenido de un artefacto para visualización.
    Retorna el archivo directamente (imágenes, videos, etc.)
    """
    artifact = await ArtifactRepository.get_by_id(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    # Construir path completo
    file_path = WORKSPACE_BASE / artifact.file_path.lstrip('/')
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    # Detectar MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type:
        mime_type = artifact.mime_type or "application/octet-stream"
    
    return FileResponse(
        path=str(file_path),
        media_type=mime_type,
        filename=artifact.file_name
    )


@router.get("/{artifact_id}/view", response_class=HTMLResponse)
async def get_artifact_viewer(artifact_id: str):
    """
    Obtiene un viewer sandboxed para el artefacto.
    Para HTML, presentaciones, y otros contenidos que requieren sandbox.
    """
    artifact = await ArtifactRepository.get_by_id(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    # Construir path completo
    file_path = WORKSPACE_BASE / artifact.file_path.lstrip('/')
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    # Para tipos que requieren sandbox
    if artifact.type in ['html', 'presentation']:
        # Leer contenido
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Error reading artifact content: {e}")
            raise HTTPException(status_code=500, detail="Error reading file")
        
        # Construir HTML sandboxed
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'unsafe-inline' 'unsafe-eval' blob:; style-src 'unsafe-inline' https:; img-src 'self' data: blob: https:; media-src 'self' blob: https:; connect-src 'self';">
            <title>{artifact.title or artifact.file_name}</title>
            <style>
                body {{ margin: 0; padding: 0; overflow: auto; }}
            </style>
        </head>
        <body>
            {content}
        </body>
        </html>
        """
        
        return HTMLResponse(content=html_content)
    
    # Para otros tipos, redirigir a content
    return Response(
        status_code=307,
        headers={"Location": f"/api/v1/artifacts/{artifact_id}/content"}
    )


@router.get("/{artifact_id}/info", response_model=ArtifactContentResponse)
async def get_artifact_info(artifact_id: str):
    """
    Obtiene información de visualización de un artefacto.
    Usado por el frontend para decidir cómo mostrar el artefacto.
    """
    artifact = await ArtifactRepository.get_by_id(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    # Determinar tipo de viewer
    viewer_type = artifact.type
    is_sandboxed = artifact.type in ['html', 'presentation']
    
    # Construir URLs
    content_url = f"/api/v1/artifacts/{artifact_id}/content"
    view_url = f"/api/v1/artifacts/{artifact_id}/view"
    
    return ArtifactContentResponse(
        artifact_id=artifact_id,
        type=artifact.type,
        title=artifact.title or artifact.file_name,
        url=view_url if is_sandboxed else content_url,
        mime_type=artifact.mime_type,
        metadata=artifact.metadata,
        is_sandboxed=is_sandboxed
    )
