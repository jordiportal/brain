"""
Generate Image Tool - Generación de imágenes con múltiples proveedores

Proveedores soportados:
- openai: DALL-E 3
- replicate: Stable Diffusion, Flux
- local: Modelos locales vía ComfyUI/Automatic1111
"""

import os
import base64
import httpx
import structlog
from typing import Dict, Any, Optional, Literal

logger = structlog.get_logger()

# Configuración de proveedores
IMAGE_PROVIDERS = {
    "openai": {
        "api_url": "https://api.openai.com/v1/images/generations",
        "models": ["dall-e-3", "dall-e-2"],
        "default_model": "dall-e-3",
        "sizes": ["1024x1024", "1792x1024", "1024x1792"],
        "default_size": "1024x1024"
    },
    "replicate": {
        "api_url": "https://api.replicate.com/v1/predictions",
        "models": ["stability-ai/sdxl", "black-forest-labs/flux-schnell"],
        "default_model": "black-forest-labs/flux-schnell"
    }
}


async def _get_openai_api_key() -> Optional[str]:
    """Obtiene la API key de OpenAI desde Strapi o variables de entorno"""
    
    # Primero intentar desde Strapi
    try:
        from src.providers.llm_provider import get_provider_by_type
        
        openai_provider = await get_provider_by_type("openai")
        if openai_provider and openai_provider.api_key:
            logger.debug("OpenAI API key loaded from Strapi for image generation")
            return openai_provider.api_key
    except Exception as e:
        logger.warning(f"Could not load OpenAI provider from Strapi: {e}")
    
    # Fallback a variable de entorno
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        logger.debug("OpenAI API key loaded from environment")
        return env_key
    
    return None


async def _get_replicate_api_key() -> Optional[str]:
    """Obtiene la API key de Replicate desde Strapi o variables de entorno"""
    
    # Primero intentar desde Strapi
    try:
        from src.providers.llm_provider import get_provider_by_type
        
        replicate_provider = await get_provider_by_type("replicate")
        if replicate_provider and replicate_provider.api_key:
            logger.debug("Replicate API key loaded from Strapi")
            return replicate_provider.api_key
    except Exception as e:
        logger.debug(f"Could not load Replicate provider from Strapi: {e}")
    
    # Fallback a variable de entorno
    env_key = os.getenv("REPLICATE_API_TOKEN")
    if env_key:
        logger.debug("Replicate API key loaded from environment")
        return env_key
    
    return None


async def generate_image(
    prompt: str,
    provider: Literal["openai", "replicate", "auto"] = "auto",
    model: Optional[str] = None,
    size: str = "1024x1024",
    quality: str = "standard",
    style: Optional[str] = None,
    negative_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """
    Genera una imagen a partir de un prompt de texto.
    
    Args:
        prompt: Descripción detallada de la imagen a generar
        provider: Proveedor a usar (openai, replicate, auto)
        model: Modelo específico (dall-e-3, flux-schnell, etc.)
        size: Tamaño de la imagen (1024x1024, 1792x1024, etc.)
        quality: Calidad (standard, hd) - solo para DALL-E 3
        style: Estilo (vivid, natural) - solo para DALL-E 3
        negative_prompt: Lo que NO debe aparecer en la imagen
    
    Returns:
        Dict con:
        - success: bool
        - image_url: URL de la imagen generada
        - image_base64: Imagen en base64 (si está disponible)
        - prompt: Prompt usado
        - provider: Proveedor usado
        - model: Modelo usado
        - revised_prompt: Prompt revisado por el modelo (si aplica)
    """
    logger.info(
        "🎨 Generating image",
        prompt=prompt[:100],
        provider=provider,
        model=model,
        size=size
    )
    
    # Auto-selección de proveedor
    if provider == "auto":
        # Preferir OpenAI si hay API key disponible (desde Strapi o env)
        openai_key = await _get_openai_api_key()
        if openai_key:
            provider = "openai"
        else:
            replicate_key = await _get_replicate_api_key()
            if replicate_key:
                provider = "replicate"
            else:
                return {
                    "success": False,
                    "error": "No hay API key configurada para generación de imágenes. Configure OPENAI_API_KEY en Strapi (Providers) o REPLICATE_API_TOKEN."
                }
    
    try:
        if provider == "openai":
            return await _generate_with_openai(
                prompt=prompt,
                model=model or "dall-e-3",
                size=size,
                quality=quality,
                style=style
            )
        elif provider == "replicate":
            return await _generate_with_replicate(
                prompt=prompt,
                model=model,
                negative_prompt=negative_prompt
            )
        else:
            return {
                "success": False,
                "error": f"Proveedor no soportado: {provider}",
                "available_providers": list(IMAGE_PROVIDERS.keys())
            }
    except Exception as e:
        logger.error(f"Error generating image: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "provider": provider,
            "prompt": prompt
        }


async def _generate_with_openai(
    prompt: str,
    model: str = "dall-e-3",
    size: str = "1024x1024",
    quality: str = "standard",
    style: Optional[str] = None
) -> Dict[str, Any]:
    """Genera imagen con DALL-E de OpenAI."""
    
    api_key = await _get_openai_api_key()
    if not api_key:
        return {
            "success": False,
            "error": "OPENAI_API_KEY no configurada. Configure en Strapi (Providers > OpenAI) o en variable de entorno."
        }
    
    payload = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "quality": quality,
        "response_format": "url"  # o "b64_json" para base64
    }
    
    if style and model == "dall-e-3":
        payload["style"] = style
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/images/generations",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        
        if response.status_code != 200:
            error_data = response.json()
            return {
                "success": False,
                "error": error_data.get("error", {}).get("message", response.text),
                "status_code": response.status_code
            }
        
        data = response.json()
        image_data = data["data"][0]
        
        result = {
            "success": True,
            "image_url": image_data.get("url"),
            "prompt": prompt,
            "provider": "openai",
            "model": model,
            "size": size
        }
        
        # DALL-E 3 puede devolver prompt revisado
        if "revised_prompt" in image_data:
            result["revised_prompt"] = image_data["revised_prompt"]
        
        logger.info(
            "✅ Image generated with OpenAI",
            model=model,
            has_url=bool(result.get("image_url"))
        )
        
        return result


async def _generate_with_replicate(
    prompt: str,
    model: Optional[str] = None,
    negative_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """Genera imagen con Replicate (Stable Diffusion, Flux, etc.)."""
    
    api_token = await _get_replicate_api_key()
    if not api_token:
        return {
            "success": False,
            "error": "REPLICATE_API_TOKEN no configurada. Configure en Strapi (Providers > Replicate) o en variable de entorno."
        }
    
    # Modelo por defecto: Flux Schnell (rápido y de calidad)
    model_version = model or "black-forest-labs/flux-schnell"
    
    # Construir input según el modelo
    input_data = {"prompt": prompt}
    if negative_prompt:
        input_data["negative_prompt"] = negative_prompt
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Crear predicción
        response = await client.post(
            "https://api.replicate.com/v1/predictions",
            headers={
                "Authorization": f"Token {api_token}",
                "Content-Type": "application/json"
            },
            json={
                "version": model_version,
                "input": input_data
            }
        )
        
        if response.status_code not in (200, 201):
            return {
                "success": False,
                "error": response.text,
                "status_code": response.status_code
            }
        
        prediction = response.json()
        prediction_id = prediction["id"]
        
        # Polling para obtener resultado
        for _ in range(60):  # Max 60 intentos (2 minutos)
            await asyncio.sleep(2)
            
            status_response = await client.get(
                f"https://api.replicate.com/v1/predictions/{prediction_id}",
                headers={"Authorization": f"Token {api_token}"}
            )
            
            status_data = status_response.json()
            
            if status_data["status"] == "succeeded":
                output = status_data.get("output", [])
                image_url = output[0] if isinstance(output, list) and output else output
                
                return {
                    "success": True,
                    "image_url": image_url,
                    "prompt": prompt,
                    "provider": "replicate",
                    "model": model_version
                }
            
            elif status_data["status"] == "failed":
                return {
                    "success": False,
                    "error": status_data.get("error", "Prediction failed"),
                    "provider": "replicate"
                }
        
        return {
            "success": False,
            "error": "Timeout waiting for image generation",
            "provider": "replicate"
        }


# Importar asyncio para el polling
import asyncio


# ============================================
# Tool Definition para el Registry
# ============================================

GENERATE_IMAGE_TOOL = {
    "id": "generate_image",
    "name": "generate_image",
    "description": "Genera una imagen a partir de una descripción en texto. Soporta DALL-E 3 (OpenAI) y Stable Diffusion/Flux (Replicate).",
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Descripción detallada de la imagen a generar. Sea específico con colores, estilo, composición, iluminación."
            },
            "provider": {
                "type": "string",
                "enum": ["openai", "replicate", "auto"],
                "default": "auto",
                "description": "Proveedor de generación. 'auto' selecciona automáticamente según disponibilidad."
            },
            "model": {
                "type": "string",
                "description": "Modelo específico (dall-e-3, dall-e-2, flux-schnell, sdxl). Si no se especifica, usa el mejor disponible."
            },
            "size": {
                "type": "string",
                "enum": ["1024x1024", "1792x1024", "1024x1792"],
                "default": "1024x1024",
                "description": "Tamaño de la imagen. 1792x1024 para paisajes, 1024x1792 para retratos."
            },
            "quality": {
                "type": "string",
                "enum": ["standard", "hd"],
                "default": "standard",
                "description": "Calidad de la imagen. 'hd' para mayor detalle (solo DALL-E 3)."
            },
            "style": {
                "type": "string",
                "enum": ["vivid", "natural"],
                "description": "Estilo: 'vivid' para colores vibrantes, 'natural' para realismo (solo DALL-E 3)."
            },
            "negative_prompt": {
                "type": "string",
                "description": "Lo que NO debe aparecer en la imagen (solo Replicate/SD)."
            }
        },
        "required": ["prompt"]
    },
    "handler": generate_image
}
