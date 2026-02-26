"""
Generate Image Tool - Generación de imágenes con múltiples proveedores

Proveedores soportados:
- gemini: Nano Banana (gemini-2.5-flash-image, gemini-3-pro-image-preview) - Google
- openai: DALL-E 3, DALL-E 2
- replicate: Stable Diffusion, Flux
- local: Modelos locales vía ComfyUI/Automatic1111
"""

import os
import base64
import httpx
import structlog
from typing import Dict, Any, Optional, Literal
from datetime import datetime
from pathlib import Path

logger = structlog.get_logger()

# Workspace path for storing generated images
WORKSPACE_PATH = Path("/workspace/images")


async def _save_image_to_workspace(
    image_data: bytes,
    prompt: str,
    provider: str,
    model: str,
    mime_type: str = "image/png",
    conversation_id: Optional[str] = None,
    agent_id: Optional[str] = "designer_agent",
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Guarda la imagen en el workspace y registra como artifact.
    Always saves to the API container (for artifact serving).
    If user_id is provided, also copies to the user's sandbox container.
    
    Returns:
        Dict con file_path, file_name, image_url (local), artifact_id
    """
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_prompt = prompt[:30].replace(' ', '_').replace('/', '_').replace('\\', '_')
        file_name = f"{provider}_{safe_prompt}_{timestamp}.png"

        # Always save to API container for artifact serving
        workspace = WORKSPACE_PATH
        workspace.mkdir(parents=True, exist_ok=True)
        file_path = workspace / file_name
        with open(file_path, 'wb') as f:
            f.write(image_data)

        # Additionally copy to the user's sandbox container
        if user_id:
            try:
                from src.code_executor.sandbox_manager import sandbox_manager
                executor = await sandbox_manager.get_or_create(user_id)
                executor.write_binary_file(f"images/{file_name}", image_data)
                logger.info("Image copied to user sandbox", user=user_id, file=file_name)
            except Exception as exc:
                logger.warning("Could not copy image to user sandbox", error=str(exc))
        
        file_size = len(image_data)
        
        # Determinar dimensiones desde bytes en memoria
        width, height = None, None
        try:
            from PIL import Image as PILImage
            import io as _io
            with PILImage.open(_io.BytesIO(image_data)) as img:
                width, height = img.size
        except Exception:
            pass
        
        # Crear registro en artifacts
        try:
            from src.artifacts import ArtifactRepository, ArtifactCreate, ArtifactType
            
            artifact_data = ArtifactCreate(
                type=ArtifactType.IMAGE,
                title=f"Imagen generada: {prompt[:50]}...",
                description=prompt,
                file_path=str(file_path),
                file_name=file_name,
                mime_type=mime_type,
                file_size=file_size,
                conversation_id=conversation_id,
                agent_id=agent_id,
                tool_id="generate_image",
                metadata={
                    "width": width,
                    "height": height,
                    "provider": provider,
                    "model": model,
                    "prompt": prompt,
                    "user_id": user_id,
                }
            )
            
            artifact = await ArtifactRepository.create(user_id or "default", artifact_data)
            
            if artifact:
                logger.info(
                    f"✅ Image saved and artifact created: {artifact.artifact_id}",
                    file_path=str(file_path),
                    file_size=file_size
                )
                
                return {
                    "file_path": str(file_path),
                    "file_name": file_name,
                    "local_url": f"/api/v1/artifacts/{artifact.artifact_id}/content",
                    "artifact_id": artifact.artifact_id,
                    "file_size": file_size,
                    "width": width,
                    "height": height
                }
        except Exception as e:
            logger.error(f"Error creating artifact record: {e}")
        
        return {
            "file_path": str(file_path),
            "file_name": file_name,
            "local_url": f"/api/v1/workspace/files/images/{file_name}",
            "file_size": file_size
        }
        
    except Exception as e:
        logger.error(f"Error saving image to workspace: {e}")
        return {"error": str(e)}

# Configuración de proveedores
IMAGE_PROVIDERS = {
    "gemini": {
        "api_url": "https://generativelanguage.googleapis.com/v1beta/models",
        "models": ["gemini-2.5-flash-image", "gemini-3-pro-image-preview"],
        "default_model": "gemini-2.5-flash-image",
        "aspect_ratios": ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
        "default_aspect_ratio": "1:1",
        "resolutions": ["1K", "2K", "4K"],  # Solo para gemini-3-pro-image-preview
        "default_resolution": "1K"
    },
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


async def _get_gemini_api_key() -> Optional[str]:
    """Obtiene la API key de Gemini desde la BD o variables de entorno"""
    
    # Primero intentar desde la BD (providers)
    try:
        from src.providers.llm_provider import get_provider_by_type
        
        gemini_provider = await get_provider_by_type("gemini")
        if gemini_provider and gemini_provider.api_key:
            logger.debug("Gemini API key loaded from database for image generation")
            return gemini_provider.api_key
    except Exception as e:
        logger.warning(f"Could not load Gemini provider from database: {e}")
    
    # Fallback a variable de entorno
    env_key = os.getenv("GEMINI_API_KEY")
    if env_key:
        logger.debug("Gemini API key loaded from environment")
        return env_key
    
    return None


async def _get_openai_api_key() -> Optional[str]:
    """Obtiene la API key de OpenAI desde la BD o variables de entorno"""
    
    # Primero intentar desde la BD (providers)
    try:
        from src.providers.llm_provider import get_provider_by_type
        
        openai_provider = await get_provider_by_type("openai")
        if openai_provider and openai_provider.api_key:
            logger.debug("OpenAI API key loaded from database for image generation")
            return openai_provider.api_key
    except Exception as e:
        logger.warning(f"Could not load OpenAI provider from database: {e}")
    
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
    provider: Literal["gemini", "openai", "replicate", "auto"] = "auto",
    model: Optional[str] = None,
    aspect_ratio: str = "1:1",
    size: str = "1024x1024",
    resolution: str = "1K",
    quality: str = "standard",
    style: Optional[str] = None,
    negative_prompt: Optional[str] = None,
    _user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Genera una imagen a partir de un prompt de texto.
    
    Args:
        prompt: Descripción detallada de la imagen a generar
        provider: Proveedor a usar (gemini, openai, replicate, auto)
                  - gemini: Nano Banana (Google) - mejor calidad y más rápido
                  - openai: DALL-E 3/2
                  - replicate: Flux/Stable Diffusion
        model: Modelo específico:
               - Gemini: gemini-2.5-flash-image (Nano Banana), gemini-3-pro-image-preview (Nano Banana Pro)
               - OpenAI: dall-e-3, dall-e-2
               - Replicate: flux-schnell, sdxl
        aspect_ratio: Relación de aspecto (1:1, 16:9, 9:16, etc.) - para Gemini
        size: Tamaño de la imagen (1024x1024, 1792x1024, etc.) - para OpenAI
        resolution: Resolución (1K, 2K, 4K) - solo para gemini-3-pro-image-preview
        quality: Calidad (standard, hd) - solo para DALL-E 3
        style: Estilo (vivid, natural) - solo para DALL-E 3
        negative_prompt: Lo que NO debe aparecer en la imagen (solo Replicate)
    
    Returns:
        Dict con:
        - success: bool
        - image_url: URL de la imagen generada
        - image_base64: Imagen en base64 (si está disponible)
        - prompt: Prompt usado
        - provider: Proveedor usado
        - model: Modelo usado
    """
    logger.info(
        "🎨 Generating image",
        prompt=prompt[:100],
        provider=provider,
        model=model
    )
    
    # Auto-selección de proveedor
    if provider == "auto":
        # Preferir Gemini (Nano Banana) si hay API key disponible
        gemini_key = await _get_gemini_api_key()
        if gemini_key:
            provider = "gemini"
        else:
            # Segundo: OpenAI
            openai_key = await _get_openai_api_key()
            if openai_key:
                provider = "openai"
            else:
                # Tercero: Replicate
                replicate_key = await _get_replicate_api_key()
                if replicate_key:
                    provider = "replicate"
                else:
                    return {
                        "success": False,
                        "error": "No hay API key configurada para generación de imágenes. Configure GEMINI_API_KEY, OPENAI_API_KEY o REPLICATE_API_TOKEN en Providers."
                    }
    
    try:
        # Generar la imagen según el proveedor
        if provider == "gemini":
            result = await _generate_with_gemini(
                prompt=prompt,
                model=model or "gemini-2.5-flash-image",
                aspect_ratio=aspect_ratio,
                resolution=resolution
            )
        elif provider == "openai":
            result = await _generate_with_openai(
                prompt=prompt,
                model=model or "dall-e-3",
                size=size,
                quality=quality,
                style=style
            )
        elif provider == "replicate":
            result = await _generate_with_replicate(
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
        
        # Si la generación falló, retornar error
        if not result.get("success"):
            return result
        
        # Guardar la imagen en el workspace y crear artifact
        image_data = None
        mime_type = "image/png"
        
        # Intentar obtener datos de la imagen
        if result.get("image_base64"):
            # Viene como base64 (Gemini)
            image_data = base64.b64decode(result["image_base64"])
            mime_type = result.get("mime_type", "image/png")
        elif result.get("image_url") and result["image_url"].startswith("data:"):
            # Data URL (base64 embed)
            data_url = result["image_url"]
            header, encoded = data_url.split(",", 1)
            image_data = base64.b64decode(encoded)
            mime_type = header.split(";")[0].replace("data:", "")
        elif result.get("image_url") and result["image_url"].startswith("http"):
            # URL externa (OpenAI, Replicate) - descargar
            async with httpx.AsyncClient() as client:
                response = await client.get(result["image_url"], timeout=30.0)
                if response.status_code == 200:
                    image_data = response.content
                    # Detectar mime type
                    content_type = response.headers.get("content-type", "image/png")
                    mime_type = content_type.split(";")[0]
        
        if image_data:
            # Ensure image_base64 is always in the result for SSE streaming
            if not result.get("image_base64"):
                result["image_base64"] = base64.b64encode(image_data).decode("utf-8")
            if not result.get("mime_type"):
                result["mime_type"] = mime_type
            
            # Guardar en workspace y crear artifact
            save_result = await _save_image_to_workspace(
                image_data=image_data,
                prompt=prompt,
                provider=provider,
                model=result.get("model", model or "unknown"),
                mime_type=mime_type,
                user_id=_user_id,
            )
            
            # Enriquecer resultado con información del archivo guardado
            if "error" not in save_result:
                result.update({
                    "local_path": save_result.get("local_url"),
                    "file_name": save_result.get("file_name"),
                    "file_size": save_result.get("file_size"),
                    "artifact_id": save_result.get("artifact_id"),
                    "width": save_result.get("width"),
                    "height": save_result.get("height"),
                    "saved_to_workspace": True
                })
        
        return result
        
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


async def _generate_with_gemini(
    prompt: str,
    model: str = "gemini-2.5-flash-image",
    aspect_ratio: str = "1:1",
    resolution: str = "1K"
) -> Dict[str, Any]:
    """Genera imagen con Gemini (Nano Banana) de Google.
    
    Modelos disponibles:
    - gemini-2.5-flash-image: Nano Banana - rápido y eficiente
    - gemini-3-pro-image-preview: Nano Banana Pro - mejor calidad, hasta 4K
    
    Documentación: https://ai.google.dev/gemini-api/docs/image-generation
    """
    
    api_key = await _get_gemini_api_key()
    if not api_key:
        return {
            "success": False,
            "error": "GEMINI_API_KEY no configurada. Configure en Providers (tipo: gemini) o en variable de entorno."
        }
    
    # Construir el payload según la API de Gemini
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt}
            ]
        }],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"]
        }
    }
    
    # Añadir configuración de imagen
    image_config = {"aspectRatio": aspect_ratio}
    
    # Solo gemini-3-pro-image-preview soporta resoluciones mayores
    if model == "gemini-3-pro-image-preview" and resolution in ["2K", "4K"]:
        image_config["imageSize"] = resolution
    
    payload["generationConfig"]["imageConfig"] = image_config
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            url,
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json"
            },
            json=payload
        )
        
        if response.status_code != 200:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", response.text)
            return {
                "success": False,
                "error": error_msg,
                "status_code": response.status_code
            }
        
        data = response.json()
        
        # Extraer la imagen de la respuesta
        result = {
            "success": True,
            "prompt": prompt,
            "provider": "gemini",
            "model": model,
            "aspect_ratio": aspect_ratio
        }
        
        # Procesar las partes de la respuesta
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            for part in parts:
                if "text" in part:
                    result["text_response"] = part["text"]
                elif "inlineData" in part:
                    inline_data = part["inlineData"]
                    mime_type = inline_data.get("mimeType", "image/png")
                    image_b64 = inline_data.get("data", "")
                    data_url = f"data:{mime_type};base64,{image_b64}"
                    # Normalizar: image_url siempre presente (igual que OpenAI/Replicate)
                    result["image_url"] = data_url
                    # Campos adicionales específicos de Gemini (por si se necesitan)
                    result["image_base64"] = image_b64
                    result["mime_type"] = mime_type
        
        if not result.get("image_url"):
            return {
                "success": False,
                "error": "No se generó imagen en la respuesta",
                "raw_response": data
            }
        
        logger.info(
            "✅ Image generated with Gemini (Nano Banana)",
            model=model,
            aspect_ratio=aspect_ratio,
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
    "description": """Genera una imagen a partir de una descripción en texto.

Proveedores disponibles:
- gemini (Nano Banana): Google Gemini - mejor calidad, rápido, soporta múltiples aspect ratios
  - gemini-2.5-flash-image: Nano Banana - rápido y eficiente
  - gemini-3-pro-image-preview: Nano Banana Pro - mejor calidad, hasta 4K
- openai: DALL-E 3/2 - clásico y fiable
- replicate: Flux/Stable Diffusion - open source

En modo 'auto' (por defecto), prioriza Gemini > OpenAI > Replicate según disponibilidad.""",
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Descripción detallada de la imagen a generar. Sea específico con colores, estilo, composición, iluminación."
            },
            "provider": {
                "type": "string",
                "enum": ["gemini", "openai", "replicate", "auto"],
                "default": "auto",
                "description": "Proveedor: 'gemini' (Nano Banana), 'openai' (DALL-E), 'replicate' (Flux/SD), 'auto' (mejor disponible)."
            },
            "model": {
                "type": "string",
                "description": "Modelo específico. Gemini: gemini-2.5-flash-image (Nano Banana), gemini-3-pro-image-preview (Nano Banana Pro). DALL-E: dall-e-3, dall-e-2. Replicate: flux-schnell, sdxl."
            },
            "aspect_ratio": {
                "type": "string",
                "enum": ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
                "default": "1:1",
                "description": "Relación de aspecto (solo Gemini). 16:9 para paisajes, 9:16 para retratos/stories, 1:1 para cuadrado."
            },
            "resolution": {
                "type": "string",
                "enum": ["1K", "2K", "4K"],
                "default": "1K",
                "description": "Resolución de salida (solo gemini-3-pro-image-preview). 4K para máxima calidad."
            },
            "size": {
                "type": "string",
                "enum": ["1024x1024", "1792x1024", "1024x1792"],
                "default": "1024x1024",
                "description": "Tamaño de la imagen (solo DALL-E). 1792x1024 para paisajes, 1024x1792 para retratos."
            },
            "quality": {
                "type": "string",
                "enum": ["standard", "hd"],
                "default": "standard",
                "description": "Calidad (solo DALL-E 3). 'hd' para mayor detalle."
            },
            "style": {
                "type": "string",
                "enum": ["vivid", "natural"],
                "description": "Estilo (solo DALL-E 3): 'vivid' para colores vibrantes, 'natural' para realismo."
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
