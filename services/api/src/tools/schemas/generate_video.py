"""
Configuration Schema for generate_video tool (Veo 3.1)

Soporta generación de vídeos con Veo 3.1 de Google:
- Text-to-video
- Image-to-video
- Frame interpolation
- Video extension
"""

from .base import (
    ToolConfigurableSchema,
    ConfigFieldSchema,
    ConfigFieldType,
    SelectOption,
    VisibilityCondition,
)


GENERATE_VIDEO_SCHEMA = ToolConfigurableSchema(
    id="generate_video",
    display_name="Generación de Vídeo",
    description="Genera vídeos de alta calidad con Veo 3.1 de Google (hasta 8 segundos, 1080p)",
    icon="videocam",
    category="media",
    requires_api_key=True,
    supported_providers=["google"],
    
    config_schema=[
        ConfigFieldSchema(
            key="provider",
            label="Proveedor",
            type=ConfigFieldType.SELECT,
            options=[
                SelectOption("google", "Google Veo 3.1")
            ],
            default="google",
            hint="Actualmente solo Google Veo está soportado",
            order=1
        ),
        
        ConfigFieldSchema(
            key="model",
            label="Modelo",
            type=ConfigFieldType.SELECT,
            options=[
                SelectOption("veo-3.1-generate-preview", "Veo 3.1 (máxima calidad)"),
                SelectOption("veo-3.1-fast-generate-preview", "Veo 3.1 Fast (más rápido)"),
                SelectOption("veo-3.0-generate-preview", "Veo 3.0"),
                SelectOption("veo-3.0-fast-generate-001", "Veo 3.0 Fast")
            ],
            default="veo-3.1-generate-preview",
            hint="Veo 3.1 ofrece mejor calidad y audio nativo",
            order=2
        ),
        
        ConfigFieldSchema(
            key="aspect_ratio",
            label="Relación de aspecto",
            type=ConfigFieldType.SELECT,
            options=[
                SelectOption("16:9", "16:9 (Horizontal/Paisaje)"),
                SelectOption("9:16", "9:16 (Vertical/Stories)")
            ],
            default="16:9",
            hint="16:9 para vídeos horizontales, 9:16 para formato móvil",
            group="Vídeo",
            order=10
        ),
        
        ConfigFieldSchema(
            key="resolution",
            label="Resolución",
            type=ConfigFieldType.SELECT,
            options=[
                SelectOption("720p", "720p HD"),
                SelectOption("1080p", "1080p Full HD")
            ],
            default="720p",
            hint="1080p solo disponible para duración de 8 segundos",
            group="Vídeo",
            order=11
        ),
        
        ConfigFieldSchema(
            key="duration_seconds",
            label="Duración",
            type=ConfigFieldType.SELECT,
            options=[
                SelectOption("4", "4 segundos"),
                SelectOption("6", "6 segundos"),
                SelectOption("8", "8 segundos (máximo)")
            ],
            default="8",
            hint="Duración del vídeo generado",
            group="Vídeo",
            order=12
        ),
        
        ConfigFieldSchema(
            key="person_generation",
            label="Generación de personas",
            type=ConfigFieldType.SELECT,
            options=[
                SelectOption("allow_all", "Permitir todas"),
                SelectOption("allow_adult", "Solo adultos"),
                SelectOption("dont_allow", "No permitir")
            ],
            default="allow_all",
            hint="Control de seguridad para generación de personas",
            group="Seguridad",
            order=20
        ),
    ],
    
    default_config={
        "provider": "google",
        "model": "veo-3.1-generate-preview",
        "aspect_ratio": "16:9",
        "resolution": "720p",
        "duration_seconds": "8",
        "person_generation": "allow_all"
    }
)
