"""
Media Domain Tools - Generación y manipulación de imágenes y vídeos

Tools:
- generate_image: Genera imágenes con DALL-E, Gemini (Nano Banana), o Replicate
- edit_image: Edita imágenes existentes con Gemini 2.5 Flash Image
- analyze_image: Analiza imágenes con LLM visual (GPT-4o, LLaVA)
- generate_video: Genera vídeos con Veo 3.1 de Google
- extend_video: Extiende vídeos generados con Veo
- check_video_status: Verifica estado de generación de vídeo
"""

from .generate_image import generate_image, GENERATE_IMAGE_TOOL
from .edit_image import edit_image, EDIT_IMAGE_TOOL
from .analyze_image import analyze_image, ANALYZE_IMAGE_TOOL
from .generate_video import (
    generate_video,
    extend_video,
    check_video_status,
    GENERATE_VIDEO_TOOL,
    EXTEND_VIDEO_TOOL,
    CHECK_VIDEO_STATUS_TOOL
)

MEDIA_TOOLS = {
    "generate_image": GENERATE_IMAGE_TOOL,
    "edit_image": EDIT_IMAGE_TOOL,
    "analyze_image": ANALYZE_IMAGE_TOOL,
    "generate_video": GENERATE_VIDEO_TOOL,
    "extend_video": EXTEND_VIDEO_TOOL,
    "check_video_status": CHECK_VIDEO_STATUS_TOOL
}

__all__ = [
    "MEDIA_TOOLS",
    "generate_image",
    "GENERATE_IMAGE_TOOL",
    "edit_image",
    "EDIT_IMAGE_TOOL",
    "analyze_image",
    "ANALYZE_IMAGE_TOOL",
    "generate_video",
    "extend_video",
    "check_video_status",
    "GENERATE_VIDEO_TOOL",
    "EXTEND_VIDEO_TOOL",
    "CHECK_VIDEO_STATUS_TOOL"
]
