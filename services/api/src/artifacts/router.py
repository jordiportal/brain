"""
Artefactos - API Router
Endpoints REST para gestión de artefactos
"""

from typing import Optional
from pathlib import Path
import mimetypes
import structlog

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse, HTMLResponse

from src.auth import get_current_user, optional_current_user, get_current_user_flexible

from .models import (
    ArtifactCreate, ArtifactUpdate, ArtifactResponse, 
    ArtifactListResponse, ArtifactContentResponse, ArtifactType
)
from .repository import ArtifactRepository

logger = structlog.get_logger()
router = APIRouter(prefix="/artifacts", tags=["artifacts"])

WORKSPACE_BASE = Path("/workspace")

SYNCFUSION_LICENSE_KEY = "Ngo9BigBOggjHTQxAR8/V1JFaF5cXGRCf1FpRmJGdld5fUVHYVZUTXxaS00DNHVRdkdmWXZcc3RWRmJZVEJ2XkRWYEA="


def _uid(user: dict) -> str:
    return user.get("email") or str(user["id"])


def _build_syncfusion_viewer(artifact, artifact_id: str) -> HTMLResponse:
    file_name = artifact.file_name
    content_url = f"/api/v1/artifacts/{artifact_id}/content"
    syncfusion_open_url = "https://document.syncfusion.com/web-services/spreadsheet-editor/api/spreadsheet/open"
    cdn_version = "32.2.4"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{artifact.title or file_name}</title>
    <link href="https://cdn.syncfusion.com/ej2/{cdn_version}/material.css" rel="stylesheet">
    <script src="https://cdn.syncfusion.com/ej2/{cdn_version}/dist/ej2.min.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5; overflow: hidden; }}
        #spreadsheet {{ width: 100%; height: 100vh; }}
        .loading {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 18px; color: #666; display: flex; flex-direction: column; align-items: center; gap: 12px; }}
        .loading .spinner {{ width: 40px; height: 40px; border: 3px solid #e0e0e0; border-top: 3px solid #1976d2; border-radius: 50%; animation: spin 1s linear infinite; }}
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
        .error {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 16px; color: #d32f2f; text-align: center; padding: 24px; background: #ffebee; border-radius: 8px; max-width: 400px; }}
    </style>
</head>
<body>
    <div id="spreadsheet"><div class="loading"><div class="spinner"></div><span>Cargando Excel...</span></div></div>
    <script>
        try {{ ej.base.registerLicense('{SYNCFUSION_LICENSE_KEY}'); }} catch(e) {{}}
        document.addEventListener('DOMContentLoaded', function() {{
            var fileUrl = "{content_url}";
            var fileName = "{file_name}";
            var openUrl = "{syncfusion_open_url}";
            var spreadsheet = new ej.spreadsheet.Spreadsheet({{
                openUrl: openUrl, allowOpen: true, allowSave: false, allowEditing: true,
                showRibbon: true, showFormulaBar: true, showSheetTabs: true,
                created: function() {{
                    fetch(fileUrl).then(function(response) {{
                        if (!response.ok) throw new Error('HTTP ' + response.status);
                        return response.blob();
                    }}).then(function(blob) {{
                        var file = new File([blob], fileName, {{ type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }});
                        spreadsheet.open({{ file: file }});
                    }}).catch(function(err) {{
                        document.getElementById('spreadsheet').innerHTML = '<div class="error">Error al cargar el archivo: ' + err.message + '</div>';
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
async def create_artifact(artifact: ArtifactCreate, user: dict = Depends(get_current_user)):
    uid = _uid(user)
    result = await ArtifactRepository.create(uid, artifact)
    if not result:
        raise HTTPException(status_code=500, detail="Error creating artifact")
    return result


@router.get("", response_model=ArtifactListResponse)
async def list_artifacts(
    conversation_id: Optional[str] = None,
    type: Optional[ArtifactType] = None,
    agent_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user_flexible),
):
    uid = _uid(user)
    artifacts = await ArtifactRepository.list_artifacts(
        uid, conversation_id=conversation_id, artifact_type=type, agent_id=agent_id, limit=limit, offset=offset
    )
    total = await ArtifactRepository.count_artifacts(uid, conversation_id=conversation_id, artifact_type=type)
    return ArtifactListResponse(artifacts=artifacts, total=total, page=offset // limit + 1, page_size=limit)


@router.get("/recent", response_model=ArtifactListResponse)
async def get_recent_artifacts(limit: int = Query(20, ge=1, le=50), user: dict = Depends(get_current_user_flexible)):
    uid = _uid(user)
    artifacts = await ArtifactRepository.get_recent(uid, limit=limit)
    return ArtifactListResponse(artifacts=artifacts, total=len(artifacts), page=1, page_size=limit)


@router.get("/conversation/{conversation_id}", response_model=ArtifactListResponse)
async def get_conversation_artifacts(
    conversation_id: str,
    type: Optional[ArtifactType] = None,
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user_flexible),
):
    uid = _uid(user)
    artifacts = await ArtifactRepository.list_artifacts(uid, conversation_id=conversation_id, artifact_type=type, limit=limit)
    return ArtifactListResponse(artifacts=artifacts, total=len(artifacts), page=1, page_size=limit)


@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(artifact_id: str, user: dict = Depends(get_current_user_flexible)):
    uid = _uid(user)
    artifact = await ArtifactRepository.get_by_id(uid, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return artifact


@router.put("/{artifact_id}", response_model=ArtifactResponse)
async def update_artifact(artifact_id: str, update: ArtifactUpdate, user: dict = Depends(get_current_user)):
    uid = _uid(user)
    result = await ArtifactRepository.update(uid, artifact_id, update)
    if not result:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return result


@router.delete("/{artifact_id}")
async def delete_artifact(artifact_id: str, soft: bool = Query(True), user: dict = Depends(get_current_user)):
    uid = _uid(user)
    success = await ArtifactRepository.delete(uid, artifact_id, soft_delete=soft)
    if not success:
        raise HTTPException(status_code=500, detail="Error deleting artifact")
    return {"status": "ok", "message": "Artifact deleted"}


@router.get("/{artifact_id}/content")
async def get_artifact_content(artifact_id: str, user: dict = Depends(get_current_user_flexible)):
    uid = _uid(user)
    artifact = await ArtifactRepository.get_by_id(uid, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    file_path = Path(artifact.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type:
        mime_type = artifact.mime_type or "application/octet-stream"

    response = FileResponse(path=str(file_path), media_type=mime_type, filename=artifact.file_name)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


@router.get("/{artifact_id}/view", response_class=HTMLResponse)
async def get_artifact_viewer(artifact_id: str, user: dict = Depends(get_current_user_flexible)):
    uid = _uid(user)
    artifact = await ArtifactRepository.get_by_id(uid, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    file_path = Path(artifact.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    if artifact.type in ['html', 'presentation']:
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Error reading artifact content: {e}")
            raise HTTPException(status_code=500, detail="Error reading file")

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'unsafe-inline' 'unsafe-eval' blob:; style-src 'unsafe-inline' https:; img-src 'self' data: blob: https:; media-src 'self' blob: https:; connect-src 'self';">
            <title>{artifact.title or artifact.file_name}</title>
            <style>body {{ margin: 0; padding: 0; overflow: auto; }}</style>
        </head>
        <body>{content}</body>
        </html>
        """
        return HTMLResponse(content=html_content)

    if artifact.type == 'spreadsheet':
        return _build_syncfusion_viewer(artifact, artifact_id)

    return Response(status_code=307, headers={"Location": f"/api/v1/artifacts/{artifact_id}/content"})


@router.get("/{artifact_id}/info", response_model=ArtifactContentResponse)
async def get_artifact_info(artifact_id: str, user: dict = Depends(get_current_user)):
    uid = _uid(user)
    artifact = await ArtifactRepository.get_by_id(uid, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    is_sandboxed = artifact.type in ['html', 'presentation', 'spreadsheet']
    content_url = f"/api/v1/artifacts/{artifact_id}/content"
    view_url = f"/api/v1/artifacts/{artifact_id}/view"

    return ArtifactContentResponse(
        artifact_id=artifact_id,
        type=artifact.type,
        title=artifact.title or artifact.file_name,
        url=view_url if is_sandboxed else content_url,
        mime_type=artifact.mime_type,
        metadata=artifact.metadata,
        is_sandboxed=is_sandboxed,
    )
