"""
Artefactos - Modelos Pydantic para gestión de archivos generados
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class ArtifactType(str, Enum):
    """Tipos de artefactos soportados"""
    IMAGE = "image"
    VIDEO = "video"
    PRESENTATION = "presentation"
    CODE = "code"
    DOCUMENT = "document"
    HTML = "html"
    AUDIO = "audio"
    FILE = "file"
    SPREADSHEET = "spreadsheet"


class ArtifactSource(str, Enum):
    """Origen del artefacto"""
    TOOL_EXECUTION = "tool_execution"
    USER_UPLOAD = "user_upload"
    CODE_EXECUTION = "code_execution"
    IMPORTED = "imported"


class ArtifactStatus(str, Enum):
    """Estado del artefacto"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ImageMetadata(BaseModel):
    """Metadata específica para imágenes"""
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None  # jpg, png, webp, etc.
    color_space: Optional[str] = None
    dpi: Optional[int] = None


class VideoMetadata(BaseModel):
    """Metadata específica para videos"""
    duration: Optional[float] = None  # segundos
    resolution: Optional[str] = None  # 1080p, 4K, etc.
    width: Optional[int] = None
    height: Optional[int] = None
    codec: Optional[str] = None
    fps: Optional[float] = None
    bitrate: Optional[str] = None


class PresentationMetadata(BaseModel):
    """Metadata específica para presentaciones"""
    slides_count: Optional[int] = None
    theme: Optional[str] = None
    has_animations: Optional[bool] = None


class DocumentMetadata(BaseModel):
    """Metadata específica para documentos"""
    pages: Optional[int] = None
    author: Optional[str] = None
    title: Optional[str] = None


class SpreadsheetMetadata(BaseModel):
    """Metadata específica para hojas de cálculo"""
    sheets_count: Optional[int] = None
    rows_count: Optional[int] = None
    columns_count: Optional[int] = None
    file_format: Optional[str] = None  # xlsx, xls, csv, etc.


class ArtifactBase(BaseModel):
    """Modelo base para artefactos"""
    artifact_id: str = Field(..., description="ID único del artefacto")
    type: ArtifactType = Field(..., description="Tipo de artefacto")
    title: Optional[str] = Field(None, description="Título descriptivo")
    description: Optional[str] = Field(None, description="Descripción")
    file_name: str = Field(..., description="Nombre del archivo")
    mime_type: Optional[str] = Field(None, description="MIME type")
    file_size: Optional[int] = Field(None, description="Tamaño en bytes")
    
    # Relaciones
    conversation_id: Optional[str] = Field(None, description="ID de conversación")
    agent_id: Optional[str] = Field(None, description="ID del agente que lo generó")
    
    # Origen
    source: ArtifactSource = Field(ArtifactSource.TOOL_EXECUTION, description="Origen")
    tool_id: Optional[str] = Field(None, description="ID de la tool que lo generó")
    
    # Metadata flexible según tipo
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata específica")
    
    # Versionado
    version: int = Field(1, description="Número de versión")
    is_latest: bool = Field(True, description="Es la versión más reciente")


class ArtifactCreate(BaseModel):
    """Modelo para crear un nuevo artefacto"""
    type: ArtifactType
    title: Optional[str] = None
    description: Optional[str] = None
    file_path: str = Field(..., description="Ruta del archivo en workspace")
    file_name: str
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    conversation_id: Optional[str] = None
    agent_id: Optional[str] = None
    source: ArtifactSource = ArtifactSource.TOOL_EXECUTION
    tool_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    parent_artifact_id: Optional[int] = None  # Para versiones


class ArtifactUpdate(BaseModel):
    """Modelo para actualizar un artefacto"""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ArtifactStatus] = None
    metadata: Optional[Dict[str, Any]] = None


class ArtifactResponse(ArtifactBase):
    """Modelo de respuesta con todos los campos"""
    id: int
    file_path: str
    parent_artifact_id: Optional[int] = None
    status: ArtifactStatus = ArtifactStatus.ACTIVE
    created_at: datetime
    updated_at: datetime
    accessed_at: datetime
    
    class Config:
        from_attributes = True


class ArtifactListResponse(BaseModel):
    """Respuesta paginada de lista de artefactos"""
    artifacts: List[ArtifactResponse]
    total: int
    page: int
    page_size: int


class ArtifactFilter(BaseModel):
    """Filtros para búsqueda de artefactos"""
    type: Optional[ArtifactType] = None
    conversation_id: Optional[str] = None
    agent_id: Optional[str] = None
    source: Optional[ArtifactSource] = None
    status: Optional[ArtifactStatus] = ArtifactStatus.ACTIVE
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None


class ArtifactContentResponse(BaseModel):
    """Respuesta con contenido del artefacto (para visualización)"""
    artifact_id: str
    type: ArtifactType
    title: Optional[str]
    url: str  # URL segura para acceder al contenido
    mime_type: Optional[str]
    metadata: Dict[str, Any]
    is_sandboxed: bool = False  # Si requiere iframe sandboxed


class ArtifactViewerConfig(BaseModel):
    """Configuración para el viewer de artefactos"""
    artifact_id: str
    viewer_type: str  # image, video, html, code, document
    sandbox_attributes: Optional[str] = None  # Atributos sandbox para HTML
    csp_headers: Optional[Dict[str, str]] = None  # Content Security Policy
    allow_scripts: bool = False
    allow_same_origin: bool = True
