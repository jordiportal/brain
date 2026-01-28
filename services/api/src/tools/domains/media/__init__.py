"""
Media Domain Tools - Generación y manipulación de imágenes

Tools:
- generate_image: Genera imágenes con DALL-E o Stable Diffusion
- analyze_image: Analiza contenido de imágenes (futuro)
- edit_image: Edita imágenes existentes (futuro)
"""

from .generate_image import generate_image, GENERATE_IMAGE_TOOL

MEDIA_TOOLS = {
    "generate_image": GENERATE_IMAGE_TOOL
}

__all__ = ["MEDIA_TOOLS", "generate_image", "GENERATE_IMAGE_TOOL"]
