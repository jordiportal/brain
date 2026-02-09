"""
Configuration Schema for generate_image tool

Soporta múltiples proveedores de generación de imágenes:
- Gemini (Nano Banana) - Google
- OpenAI (DALL-E)
- Replicate (Flux/SD)
"""

from .base import (
    ToolConfigurableSchema,
    ConfigFieldSchema,
    ConfigFieldType,
    SelectOption,
    VisibilityCondition,
)


GENERATE_IMAGE_SCHEMA = ToolConfigurableSchema(
    id="generate_image",
    display_name="Generación de Imágenes",
    description="Genera imágenes con IA usando múltiples proveedores (Gemini, DALL-E, Flux)",
    icon="image",
    category="media",
    requires_api_key=True,
    supported_providers=["gemini", "openai", "replicate"],
    
    config_schema=[
        ConfigFieldSchema(
            key="provider",
            label="Proveedor",
            type=ConfigFieldType.SELECT,
            options=[
                SelectOption("auto", "Auto (mejor disponible)"),
                SelectOption("gemini", "Gemini - Nano Banana (recomendado)"),
                SelectOption("openai", "OpenAI (DALL-E)"),
                SelectOption("replicate", "Replicate (Flux/SD)")
            ],
            default="auto",
            hint="Auto prioriza: Gemini > OpenAI > Replicate según disponibilidad de API keys",
            order=1
        ),
        
        ConfigFieldSchema(
            key="model",
            label="Modelo",
            type=ConfigFieldType.SELECT,
            options_depend_on="provider",
            dynamic_options={
                "auto": [
                    SelectOption("", "Por defecto del proveedor"),
                ],
                "gemini": [
                    SelectOption("", "Por defecto (gemini-2.5-flash-image)"),
                    SelectOption("gemini-2.5-flash-image", "Nano Banana (rápido)"),
                    SelectOption("gemini-3-pro-image-preview", "Nano Banana Pro (mejor calidad, hasta 4K)")
                ],
                "openai": [
                    SelectOption("", "Por defecto (dall-e-3)"),
                    SelectOption("dall-e-3", "DALL-E 3 (mejor calidad)"),
                    SelectOption("dall-e-2", "DALL-E 2 (más rápido)")
                ],
                "replicate": [
                    SelectOption("", "Por defecto (flux-schnell)"),
                    SelectOption("flux-schnell", "Flux Schnell (rápido)"),
                    SelectOption("flux-dev", "Flux Dev (mejor calidad)"),
                    SelectOption("sdxl", "Stable Diffusion XL")
                ]
            },
            default="",
            hint="Dejar vacío para usar el modelo por defecto del proveedor",
            order=2
        ),
        
        # Opciones específicas de Gemini
        ConfigFieldSchema(
            key="aspect_ratio",
            label="Relación de aspecto",
            type=ConfigFieldType.SELECT,
            options=[
                SelectOption("1:1", "1:1 (Cuadrado)"),
                SelectOption("16:9", "16:9 (Paisaje)"),
                SelectOption("9:16", "9:16 (Retrato/Stories)"),
                SelectOption("4:3", "4:3 (Estándar)"),
                SelectOption("3:4", "3:4 (Retrato)"),
                SelectOption("3:2", "3:2 (Foto)"),
                SelectOption("2:3", "2:3 (Retrato foto)"),
                SelectOption("21:9", "21:9 (Ultrawide)")
            ],
            default="1:1",
            visible_when=VisibilityCondition(field="provider", values=["gemini", "auto"]),
            hint="Solo disponible para Gemini (Nano Banana)",
            group="Gemini",
            order=10
        ),
        
        ConfigFieldSchema(
            key="resolution",
            label="Resolución",
            type=ConfigFieldType.SELECT,
            options=[
                SelectOption("1K", "1K (estándar)"),
                SelectOption("2K", "2K (alta)"),
                SelectOption("4K", "4K (máxima)")
            ],
            default="1K",
            visible_when=VisibilityCondition(field="model", value="gemini-3-pro-image-preview"),
            hint="Solo para Nano Banana Pro (gemini-3-pro-image-preview)",
            group="Gemini",
            order=11
        ),
        
        # Opciones específicas de DALL-E
        ConfigFieldSchema(
            key="size",
            label="Tamaño",
            type=ConfigFieldType.SELECT,
            options=[
                SelectOption("1024x1024", "1024x1024 (Cuadrado)"),
                SelectOption("1792x1024", "1792x1024 (Paisaje)"),
                SelectOption("1024x1792", "1024x1792 (Retrato)")
            ],
            default="1024x1024",
            visible_when=VisibilityCondition(field="provider", value="openai"),
            hint="Tamaño de salida para DALL-E",
            group="DALL-E",
            order=20
        ),
        
        ConfigFieldSchema(
            key="quality",
            label="Calidad",
            type=ConfigFieldType.SELECT,
            options=[
                SelectOption("standard", "Estándar"),
                SelectOption("hd", "HD (más detalle)")
            ],
            default="standard",
            visible_when=VisibilityCondition(field="provider", value="openai"),
            hint="Solo para DALL-E 3",
            group="DALL-E",
            order=21
        ),
        
        ConfigFieldSchema(
            key="style",
            label="Estilo",
            type=ConfigFieldType.SELECT,
            options=[
                SelectOption("vivid", "Vivid (colores vibrantes)"),
                SelectOption("natural", "Natural (más realista)")
            ],
            default="vivid",
            visible_when=VisibilityCondition(field="provider", value="openai"),
            hint="Solo para DALL-E 3",
            group="DALL-E",
            order=22
        ),
        
        # Opciones específicas de Replicate/SD
        ConfigFieldSchema(
            key="negative_prompt",
            label="Prompt negativo",
            type=ConfigFieldType.TEXT,
            default="",
            visible_when=VisibilityCondition(field="provider", value="replicate"),
            hint="Lo que NO debe aparecer en la imagen (solo Replicate/SD)",
            placeholder="blurry, low quality, distorted...",
            group="Replicate",
            order=30
        ),
    ],
    
    default_config={
        "provider": "auto",
        "model": "",
        "aspect_ratio": "1:1",
        "resolution": "1K",
        "size": "1024x1024",
        "quality": "standard",
        "style": "vivid",
        "negative_prompt": ""
    }
)
