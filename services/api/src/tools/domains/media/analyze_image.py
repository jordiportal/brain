"""
Analyze Image Tool - Análisis de imágenes con LLM visual

Usa modelos con capacidad de visión (GPT-4o, Claude 3, Llama Vision) 
para interpretar y analizar imágenes.
"""

import os
import base64
import httpx
import structlog
from typing import Dict, Any, Optional, Literal
from pathlib import Path

logger = structlog.get_logger()


async def _encode_image_to_base64(image_source: str) -> tuple[str, str]:
    """
    Codifica una imagen a base64.
    
    Args:
        image_source: URL, path local, o base64 existente
        
    Returns:
        Tuple de (base64_data, media_type)
    """
    # Si ya es base64
    if image_source.startswith("data:image"):
        # Extraer el tipo y los datos
        parts = image_source.split(",", 1)
        media_type = parts[0].split(":")[1].split(";")[0]
        return parts[1], media_type
    
    # Si es URL
    if image_source.startswith(("http://", "https://")):
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(image_source)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "image/png")
            return base64.b64encode(response.content).decode(), content_type
    
    # Si es path local
    path = Path(image_source)
    if path.exists():
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        
        # Detectar tipo por extensión
        ext = path.suffix.lower()
        media_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp"
        }
        media_type = media_types.get(ext, "image/png")
        return data, media_type
    
    raise ValueError(f"No se puede procesar la imagen: {image_source}")


async def _get_openai_api_key() -> Optional[str]:
    """Obtiene la API key de OpenAI desde Strapi o variables de entorno"""
    try:
        from src.providers.llm_provider import get_provider_by_type
        openai_provider = await get_provider_by_type("openai")
        if openai_provider and openai_provider.api_key:
            return openai_provider.api_key
    except Exception as e:
        logger.warning(f"Could not load OpenAI provider from Strapi: {e}")
    
    return os.getenv("OPENAI_API_KEY")


async def analyze_image(
    image: str,
    question: str = "Describe esta imagen en detalle",
    analysis_type: Literal["describe", "critique", "extract", "compare"] = "describe",
    context: Optional[str] = None,
    provider: Literal["openai", "ollama"] = "openai",
    model: Optional[str] = None,
    llm_url: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analiza una imagen usando un LLM con capacidad visual.
    
    Args:
        image: URL, path local, o base64 de la imagen
        question: Pregunta o instrucción sobre la imagen
        analysis_type: Tipo de análisis:
            - describe: Descripción general
            - critique: Crítica de diseño/calidad
            - extract: Extracción de texto/datos
            - compare: Comparación con expectativas (usar context)
        context: Contexto adicional (ej: "debería ser un logo minimalista")
        provider: Proveedor del LLM (openai, ollama)
        model: Modelo específico (default: gpt-4o para openai, llava para ollama)
        llm_url: URL del LLM (para ollama)
        api_key: API key (para openai)
        
    Returns:
        Dict con análisis, puntuación y sugerencias
    """
    logger.info("🔍 analyze_image called", 
                analysis_type=analysis_type, 
                provider=provider,
                has_context=bool(context))
    
    try:
        # Codificar imagen
        image_base64, media_type = await _encode_image_to_base64(image)
        
        # Construir el prompt según el tipo de análisis
        system_prompts = {
            "describe": """Eres un experto en análisis visual. Describe la imagen con detalle:
- Contenido principal
- Colores y composición
- Estilo y técnica
- Elementos destacados""",
            
            "critique": """Eres un crítico de diseño profesional. Evalúa la imagen considerando:
- Calidad técnica (resolución, nitidez, composición)
- Efectividad del diseño (claridad del mensaje, jerarquía visual)
- Estética (armonía de colores, balance, modernidad)
- Áreas de mejora

Proporciona una puntuación del 1-10 y sugerencias concretas.""",
            
            "extract": """Eres un experto en extracción de información visual. Extrae de la imagen:
- Todo texto visible (OCR)
- Datos numéricos o gráficos
- Logotipos o marcas identificables
- Estructuras o diagramas""",
            
            "compare": """Eres un evaluador de calidad de diseño. Compara la imagen con las expectativas proporcionadas.
Evalúa:
- ¿Cumple con los requisitos especificados?
- ¿Qué elementos coinciden con lo esperado?
- ¿Qué elementos difieren o faltan?
- Puntuación de coincidencia (1-10)
- Sugerencias de mejora si es necesario"""
        }
        
        system_prompt = system_prompts.get(analysis_type, system_prompts["describe"])
        
        # Construir pregunta con contexto
        full_question = question
        if context:
            full_question = f"{question}\n\nContexto/Expectativas: {context}"
        
        # Llamar al LLM según proveedor
        if provider == "openai":
            result = await _analyze_with_openai(
                image_base64, media_type, system_prompt, full_question,
                model or "gpt-4o", api_key
            )
        else:  # ollama
            result = await _analyze_with_ollama(
                image_base64, media_type, system_prompt, full_question,
                model or "llava", llm_url or "http://localhost:11434"
            )
        
        return {
            "success": True,
            "analysis_type": analysis_type,
            "analysis": result["content"],
            "model": result["model"],
            "provider": provider
        }
        
    except Exception as e:
        logger.error(f"analyze_image error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "analysis_type": analysis_type
        }


async def _analyze_with_openai(
    image_base64: str,
    media_type: str,
    system_prompt: str,
    question: str,
    model: str,
    api_key: Optional[str]
) -> Dict[str, Any]:
    """Analiza imagen con OpenAI GPT-4 Vision"""
    
    api_key = api_key or await _get_openai_api_key()
    if not api_key:
        raise ValueError("OpenAI API key no configurada")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": question},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{image_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 2000
            }
        )
        response.raise_for_status()
        data = response.json()
        
        return {
            "content": data["choices"][0]["message"]["content"],
            "model": model
        }


async def _analyze_with_ollama(
    image_base64: str,
    media_type: str,
    system_prompt: str,
    question: str,
    model: str,
    llm_url: str
) -> Dict[str, Any]:
    """Analiza imagen con Ollama (llava, bakllava, etc.)"""
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{llm_url}/api/generate",
            json={
                "model": model,
                "prompt": f"{system_prompt}\n\n{question}",
                "images": [image_base64],
                "stream": False
            }
        )
        response.raise_for_status()
        data = response.json()
        
        return {
            "content": data.get("response", ""),
            "model": model
        }


# Definición de la tool para el registry
ANALYZE_IMAGE_TOOL = {
    "id": "analyze_image",
    "name": "analyze_image",
    "description": """Analiza una imagen usando un LLM con capacidad visual (GPT-4o, LLaVA).

Tipos de análisis disponibles:
- describe: Descripción detallada del contenido
- critique: Evaluación de calidad y diseño (incluye puntuación 1-10)
- extract: Extracción de texto, datos, logos
- compare: Comparación con expectativas (requiere context)

Usa 'critique' para auto-evaluar imágenes generadas.
Usa 'compare' para verificar si el resultado cumple los requisitos.""",
    "type": "function",
    "parameters": {
        "type": "object",
        "properties": {
            "image": {
                "type": "string",
                "description": "URL, path local, o data:image base64 de la imagen a analizar"
            },
            "question": {
                "type": "string",
                "description": "Pregunta o instrucción específica sobre la imagen",
                "default": "Describe esta imagen en detalle"
            },
            "analysis_type": {
                "type": "string",
                "enum": ["describe", "critique", "extract", "compare"],
                "description": "Tipo de análisis: describe, critique (evaluación), extract (OCR), compare",
                "default": "describe"
            },
            "context": {
                "type": "string",
                "description": "Contexto o expectativas para comparación (útil con analysis_type='compare')"
            }
        },
        "required": ["image"]
    },
    "handler": analyze_image
}
