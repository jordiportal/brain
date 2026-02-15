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

# Syncfusion license key (provided by user)
SYNCFUSION_LICENSE_KEY = "Ngo9BigBOggjHTQxAR8/V1JFaF5cXGRCf1FpRmJGdld5fUVHYVZUTXxaS00DNHVRdkdmWXZcc3RWRmJZVEJ2XkRWYEA="


def _build_syncfusion_viewer(artifact, artifact_id: str) -> HTMLResponse:
    """
    Construye un HTML viewer usando Syncfusion Spreadsheet (vanilla JS via CDN).
    
    Patron oficial de Syncfusion para abrir archivos remotos:
      1. Crear Spreadsheet con openUrl (servicio server-side de procesamiento)
      2. Fetch del blob desde nuestra API
      3. Convertir blob a File object
      4. Llamar spreadsheet.open({ file }) en el evento created
    
    Ref: https://ej2.syncfusion.com/documentation/spreadsheet/open-save
    """
    file_name = artifact.file_name
    
    # URL del contenido del artefacto
    content_url = f"/api/v1/artifacts/{artifact_id}/content"
    
    # Syncfusion open URL - servicio server-side que procesa el Excel y devuelve JSON
    syncfusion_open_url = "https://document.syncfusion.com/web-services/spreadsheet-editor/api/spreadsheet/open"
    
    # Version CDN alineada con la version del package (32.x)
    cdn_version = "32.2.4"
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{artifact.title or file_name}</title>
    
    <!-- Syncfusion CSS - v{cdn_version} -->
    <link href="https://cdn.syncfusion.com/ej2/{cdn_version}/material.css" rel="stylesheet">
    
    <!-- Syncfusion Scripts - bundle completo (incluye spreadsheet) -->
    <script src="https://cdn.syncfusion.com/ej2/{cdn_version}/dist/ej2.min.js"></script>
    
    <style>
        body {{ 
            margin: 0; 
            padding: 0; 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            overflow: hidden;
        }}
        #spreadsheet {{ 
            width: 100%; 
            height: 100vh; 
        }}
        .loading {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 18px;
            color: #666;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 12px;
        }}
        .loading .spinner {{
            width: 40px;
            height: 40px;
            border: 3px solid #e0e0e0;
            border-top: 3px solid #1976d2;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        .error {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 16px;
            color: #d32f2f;
            text-align: center;
            padding: 24px;
            background: #ffebee;
            border-radius: 8px;
            max-width: 400px;
        }}
    </style>
</head>
<body>
    <div id="spreadsheet">
        <div class="loading">
            <div class="spinner"></div>
            <span>Cargando Excel...</span>
        </div>
    </div>
    
    <script>
        // Registrar licencia Syncfusion
        try {{
            ej.base.registerLicense('{SYNCFUSION_LICENSE_KEY}');
        }} catch(e) {{
            // Silenciar para no romper la app
        }}
        
        document.addEventListener('DOMContentLoaded', function() {{
            var fileUrl = "{content_url}";
            var fileName = "{file_name}";
            var openUrl = "{syncfusion_open_url}";
            
            // Crear Spreadsheet con openUrl (OBLIGATORIO para que open() funcione)
            // Ref: https://ej2.syncfusion.com/documentation/spreadsheet/open-save
            var spreadsheet = new ej.spreadsheet.Spreadsheet({{
                openUrl: openUrl,
                allowOpen: true,
                allowSave: false,
                allowEditing: true,
                showRibbon: true,
                showFormulaBar: true,
                showSheetTabs: true,
                created: function() {{
                    // Patron oficial: fetch blob -> new File([blob]) -> spreadsheet.open({{ file }})
                    fetch(fileUrl)
                        .then(function(response) {{
                            if (!response.ok) throw new Error('HTTP ' + response.status);
                            return response.blob();
                        }})
                        .then(function(blob) {{
                            // Convertir blob a File object (requerido por Syncfusion)
                            var file = new File([blob], fileName, {{
                                type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                            }});
                            // Syncfusion envia el File al openUrl para procesamiento server-side
                            spreadsheet.open({{ file: file }});
                        }})
                        .catch(function(err) {{
                            console.error('Error loading spreadsheet:', err);
                            document.getElementById('spreadsheet').innerHTML = 
                                '<div class="error">Error al cargar el archivo: ' + err.message + '</div>';
                        }});
                }}
            }});
            
            spreadsheet.appendTo('#spreadsheet');
        }});
    </script>
</body>
</html>"""
    
    return HTMLResponse(content=html_content)


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
    # El file_path en BD ya es absoluto (/workspace/images/...), usarlo directamente
    file_path = Path(artifact.file_path)
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    # Detectar MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type:
        mime_type = artifact.mime_type or "application/octet-stream"
    
    # Create response with CORS headers
    response = FileResponse(
        path=str(file_path),
        media_type=mime_type,
        filename=artifact.file_name
    )
    
    # Add CORS headers manually for blob requests
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    
    return response


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
    # El file_path en BD ya es absoluto (/workspace/images/...), usarlo directamente
    file_path = Path(artifact.file_path)
    
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
    
    # Para spreadsheets, usar Syncfusion viewer
    if artifact.type == 'spreadsheet':
        return _build_syncfusion_viewer(artifact, artifact_id)
    
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
    is_sandboxed = artifact.type in ['html', 'presentation', 'spreadsheet']
    
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
