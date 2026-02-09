"""
Configuration Schema for analyze_image tool

Soporta múltiples proveedores de análisis visual:
- OpenAI (GPT-4o, GPT-4 Vision)
- Ollama (LLaVA, BakLLaVA)
- Anthropic (Claude 3)
"""

from .base import (
    ToolConfigurableSchema,
    ConfigFieldSchema,
    ConfigFieldType,
    SelectOption,
    VisibilityCondition,
)


ANALYZE_IMAGE_SCHEMA = ToolConfigurableSchema(
    id="analyze_image",
    display_name="Análisis de Imágenes",
    description="Analiza imágenes usando modelos de visión (GPT-4o, LLaVA, Claude)",
    icon="visibility",
    category="ai",
    requires_api_key=True,
    supported_providers=["openai", "ollama", "anthropic"],
    
    config_schema=[
        ConfigFieldSchema(
            key="provider",
            label="Proveedor",
            type=ConfigFieldType.SELECT,
            options=[
                SelectOption("openai", "OpenAI (GPT-4o - recomendado)"),
                SelectOption("ollama", "Ollama (LLaVA - local)"),
                SelectOption("anthropic", "Anthropic (Claude 3)")
            ],
            default="openai",
            hint="OpenAI GPT-4o ofrece el mejor análisis. Ollama es local y gratuito.",
            order=1
        ),
        
        ConfigFieldSchema(
            key="model",
            label="Modelo",
            type=ConfigFieldType.SELECT,
            options_depend_on="provider",
            dynamic_options={
                "openai": [
                    SelectOption("gpt-4o", "GPT-4o (recomendado)"),
                    SelectOption("gpt-4o-mini", "GPT-4o Mini (más rápido)"),
                    SelectOption("gpt-4-turbo", "GPT-4 Turbo")
                ],
                "ollama": [
                    SelectOption("llava", "LLaVA (7B)"),
                    SelectOption("llava:13b", "LLaVA 13B (más capaz)"),
                    SelectOption("llava:34b", "LLaVA 34B (mejor calidad)"),
                    SelectOption("bakllava", "BakLLaVA")
                ],
                "anthropic": [
                    SelectOption("claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet (recomendado)"),
                    SelectOption("claude-3-opus-20240229", "Claude 3 Opus (más capaz)"),
                    SelectOption("claude-3-haiku-20240307", "Claude 3 Haiku (más rápido)")
                ]
            },
            default="gpt-4o",
            hint="Modelo de visión a utilizar",
            order=2
        ),
        
        # Opciones de Ollama
        ConfigFieldSchema(
            key="llm_url",
            label="URL de Ollama",
            type=ConfigFieldType.TEXT,
            default="http://localhost:11434",
            visible_when=VisibilityCondition(field="provider", value="ollama"),
            hint="URL del servidor Ollama",
            placeholder="http://localhost:11434",
            group="Ollama",
            order=10
        ),
        
        # Opciones de análisis
        ConfigFieldSchema(
            key="default_analysis_type",
            label="Tipo de análisis por defecto",
            type=ConfigFieldType.SELECT,
            options=[
                SelectOption("describe", "Descripción detallada"),
                SelectOption("critique", "Crítica de diseño (con puntuación)"),
                SelectOption("extract", "Extracción de texto/datos (OCR)"),
                SelectOption("compare", "Comparación con expectativas")
            ],
            default="describe",
            hint="Tipo de análisis cuando no se especifica",
            group="Análisis",
            order=20
        ),
        
        ConfigFieldSchema(
            key="detail_level",
            label="Nivel de detalle",
            type=ConfigFieldType.SELECT,
            options=[
                SelectOption("low", "Bajo (más rápido)"),
                SelectOption("high", "Alto (más detallado)")
            ],
            default="high",
            visible_when=VisibilityCondition(field="provider", value="openai"),
            hint="Nivel de detalle para análisis con OpenAI",
            group="Análisis",
            order=21
        ),
    ],
    
    default_config={
        "provider": "openai",
        "model": "gpt-4o",
        "llm_url": "http://localhost:11434",
        "default_analysis_type": "describe",
        "detail_level": "high"
    }
)
