"""
Generate Video Tool - Generación de vídeos con Veo 3.1 (Google)

Capacidades:
- text-to-video: Generar vídeos desde prompts de texto
- image-to-video: Animar imágenes existentes
- video-extension: Extender vídeos generados previamente
- frame-interpolation: Generar vídeo entre dos frames

Modelos disponibles:
- veo-3.1-generate-preview: Máxima calidad, 8s, 720p/1080p
- veo-3.1-fast-generate-preview: Más rápido, menor calidad
"""

import os
import asyncio
import base64
import httpx
import structlog
from typing import Dict, Any, Optional, Literal, List
from datetime import datetime
from pathlib import Path

logger = structlog.get_logger()

# Workspace path for storing generated videos
WORKSPACE_PATH = Path("/workspace/videos")


async def _save_video_as_artifact(
    video_bytes: bytes,
    prompt: str,
    provider: str,
    model: str,
    mime_type: str,
    duration_seconds: int,
    aspect_ratio: str,
    resolution: str,
    conversation_id: Optional[str] = None,
    agent_id: Optional[str] = "designer_agent",
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Guarda el video en el workspace y registra como artifact.
    
    Returns:
        Dict con file_path, file_name, video_url, artifact_id
    """
    try:
        # Asegurar que el directorio existe
        WORKSPACE_PATH.mkdir(parents=True, exist_ok=True)
        
        # Generar nombre de archivo único
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_prompt = prompt[:30].replace(' ', '_').replace('/', '_').replace('\\', '_')
        file_name = f"{provider}_{safe_prompt}_{timestamp}.mp4"
        file_path = WORKSPACE_PATH / file_name
        
        # Guardar archivo
        with open(file_path, 'wb') as f:
            f.write(video_bytes)
        
        file_size = len(video_bytes)
        
        # Crear registro en artifacts
        try:
            from src.artifacts import ArtifactRepository, ArtifactCreate, ArtifactType
            
            artifact_data = ArtifactCreate(
                type=ArtifactType.VIDEO,
                title=f"Video generado: {prompt[:50]}...",
                description=prompt,
                file_path=f"/workspace/videos/{file_name}",
                file_name=file_name,
                mime_type=mime_type,
                file_size=file_size,
                conversation_id=conversation_id,
                agent_id=agent_id,
                tool_id="generate_video",
                metadata={
                    "duration": duration_seconds,
                    "resolution": resolution,
                    "aspect_ratio": aspect_ratio,
                    "provider": provider,
                    "model": model,
                    "prompt": prompt
                }
            )
            
            artifact = await ArtifactRepository.create(user_id or "default", artifact_data)
            
            if artifact:
                logger.info(
                    f"✅ Video saved and artifact created: {artifact.artifact_id}",
                    file_path=str(file_path),
                    file_size=file_size
                )
                
                return {
                    "file_path": str(file_path),
                    "file_name": file_name,
                    "local_url": f"/workspace/videos/{file_name}",
                    "artifact_id": artifact.artifact_id,
                    "file_size": file_size
                }
        except Exception as e:
            logger.error(f"Error creating artifact record: {e}")
            # Continuar sin registro de artifact si falla
        
        return {
            "file_path": str(file_path),
            "file_name": file_name,
            "local_url": f"/workspace/videos/{file_name}",
            "file_size": file_size
        }
        
    except Exception as e:
        logger.error(f"Error saving video to workspace: {e}")
        return {"error": str(e)}

# Configuración de Veo
VEO_CONFIG = {
    "api_url": "https://generativelanguage.googleapis.com/v1beta/models",
    "models": [
        "veo-3.1-generate-preview",
        "veo-3.1-fast-generate-preview",
        "veo-3.0-generate-preview",
        "veo-3.0-fast-generate-001"
    ],
    "default_model": "veo-3.1-generate-preview",
    "aspect_ratios": ["16:9", "9:16"],
    "default_aspect_ratio": "16:9",
    "resolutions": ["720p", "1080p"],
    "default_resolution": "720p",
    "durations": [4, 6, 8],
    "default_duration": 8,
    "max_polling_time": 600,  # 10 minutos máximo
    "polling_interval": 10   # Cada 10 segundos
}


async def _get_gemini_api_key() -> Optional[str]:
    """Obtiene la API key de Gemini desde la BD o variables de entorno"""
    
    try:
        from src.providers.llm_provider import get_provider_by_type
        
        gemini_provider = await get_provider_by_type("gemini")
        if gemini_provider and gemini_provider.api_key:
            logger.debug("Gemini API key loaded from database for video generation")
            return gemini_provider.api_key
    except Exception as e:
        logger.warning(f"Could not load Gemini provider from database: {e}")
    
    env_key = os.getenv("GEMINI_API_KEY")
    if env_key:
        logger.debug("Gemini API key loaded from environment")
        return env_key
    
    return None


async def _start_video_generation(
    prompt: str,
    model: str,
    api_key: str,
    negative_prompt: Optional[str] = None,
    aspect_ratio: str = "16:9",
    resolution: str = "720p",
    duration_seconds: int = 8,
    image_data: Optional[str] = None,  # Base64 de imagen inicial
    last_frame_data: Optional[str] = None,  # Base64 de último frame
    reference_images: Optional[List[str]] = None,  # Lista de base64
    person_generation: str = "allow_all"
) -> Dict[str, Any]:
    """
    Inicia la generación de vídeo y devuelve el nombre de la operación.
    
    Returns:
        Dict con operation_name para polling
    """
    url = f"{VEO_CONFIG['api_url']}/{model}:predictLongRunning"
    
    # Construir instancia
    instance: Dict[str, Any] = {"prompt": prompt}
    
    # Añadir imagen inicial si existe
    if image_data:
        instance["image"] = {
            "bytesBase64Encoded": image_data,
            "mimeType": "image/png"
        }
    
    # Construir parámetros
    parameters: Dict[str, Any] = {
        "aspectRatio": aspect_ratio,
        "durationSeconds": int(duration_seconds),
        "personGeneration": person_generation
    }
    
    if resolution:
        parameters["resolution"] = resolution
    
    if negative_prompt:
        parameters["negativePrompt"] = negative_prompt
    
    # Último frame para interpolación
    if last_frame_data:
        parameters["lastFrame"] = {
            "bytesBase64Encoded": last_frame_data,
            "mimeType": "image/png"
        }
    
    # Imágenes de referencia (solo Veo 3.1)
    if reference_images and "3.1" in model:
        parameters["referenceImages"] = [
            {
                "image": {"bytesBase64Encoded": img, "mimeType": "image/png"},
                "referenceType": "asset"
            }
            for img in reference_images[:3]  # Máximo 3
        ]
    
    payload = {
        "instances": [instance],
        "parameters": parameters
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, json=payload, headers=headers)
        
        if response.status_code != 200:
            error_detail = response.text
            logger.error(f"Veo API error: {response.status_code}", detail=error_detail)
            return {
                "success": False,
                "error": f"API error {response.status_code}: {error_detail}"
            }
        
        data = response.json()
        operation_name = data.get("name")
        
        if not operation_name:
            return {
                "success": False,
                "error": "No operation name returned from API"
            }
        
        return {
            "success": True,
            "operation_name": operation_name
        }


async def _poll_operation(
    operation_name: str,
    api_key: str,
    max_time: int = 600,
    interval: int = 10
) -> Dict[str, Any]:
    """
    Polling de la operación hasta que complete o timeout.
    
    Returns:
        Dict con el resultado del vídeo generado
    """
    base_url = "https://generativelanguage.googleapis.com/v1beta"
    url = f"{base_url}/{operation_name}"
    
    headers = {"x-goog-api-key": api_key}
    
    elapsed = 0
    async with httpx.AsyncClient(timeout=30) as client:
        while elapsed < max_time:
            try:
                response = await client.get(url, headers=headers)
                
                if response.status_code != 200:
                    logger.warning(f"Polling error: {response.status_code}")
                    await asyncio.sleep(interval)
                    elapsed += interval
                    continue
                
                data = response.json()
                
                if data.get("done"):
                    # Operación completada
                    if "error" in data:
                        return {
                            "success": False,
                            "error": data["error"].get("message", "Unknown error")
                        }
                    
                    # Extraer URI del vídeo
                    response_data = data.get("response", {})
                    video_response = response_data.get("generateVideoResponse", {})
                    samples = video_response.get("generatedSamples", [])
                    
                    if samples:
                        video_uri = samples[0].get("video", {}).get("uri")
                        return {
                            "success": True,
                            "video_uri": video_uri,
                            "operation_name": operation_name
                        }
                    
                    return {
                        "success": False,
                        "error": "No video samples in response"
                    }
                
                # Aún procesando
                logger.info(f"Video generation in progress... ({elapsed}s elapsed)")
                await asyncio.sleep(interval)
                elapsed += interval
                
            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(interval)
                elapsed += interval
    
    return {
        "success": False,
        "error": f"Timeout after {max_time} seconds"
    }


async def _download_video(video_uri: str, api_key: str) -> Dict[str, Any]:
    """
    Descarga el vídeo generado.
    
    Returns:
        Dict con video_bytes y mime_type
    """
    headers = {"x-goog-api-key": api_key}
    
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        try:
            response = await client.get(video_uri, headers=headers)
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Download failed: {response.status_code}"
                }
            
            video_bytes = response.content
            
            # Detectar mime type
            content_type = response.headers.get("content-type", "video/mp4")
            
            return {
                "success": True,
                "video_bytes": video_bytes,
                "mime_type": content_type,
                "size_bytes": len(video_bytes)
            }
            
        except Exception as e:
            logger.error(f"Video download error: {e}")
            return {
                "success": False,
                "error": str(e)
            }


def _save_video_to_workspace(video_bytes: bytes, filename: str, user_id: Optional[str] = None) -> Optional[str]:
    """
    Guarda el vídeo en el workspace del sandbox del usuario.
    Falls back to shared persistent-runner if no user_id.
    """
    try:
        if user_id:
            import asyncio
            from src.code_executor.sandbox_manager import sandbox_manager
            executor = asyncio.get_event_loop().run_until_complete(
                sandbox_manager.get_or_create(user_id)
            )
        else:
            from src.code_executor.persistent_executor import PersistentCodeExecutor
            executor = PersistentCodeExecutor()

        file_path = f"media/videos/{filename}"

        if executor.write_binary_file(file_path, video_bytes):
            logger.info(f"Video saved to workspace: {file_path}")
            return file_path
        else:
            logger.error("Failed to save video to workspace")
            return None

    except Exception as e:
        logger.error(f"Error saving video to workspace: {e}")
        return None


async def generate_video(
    prompt: str,
    negative_prompt: Optional[str] = None,
    model: Optional[str] = None,
    aspect_ratio: Optional[str] = None,
    resolution: Optional[str] = None,
    duration_seconds: Optional[int] = None,
    image: Optional[str] = None,
    last_frame: Optional[str] = None,
    reference_images: Optional[List[str]] = None,
    person_generation: str = "allow_all",
    wait_for_completion: bool = True,
    api_key: Optional[str] = None,
    _user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Genera un vídeo usando Veo 3.1 de Google.
    
    Args:
        prompt: Descripción del vídeo a generar. Puede incluir diálogos entre comillas.
        negative_prompt: Qué evitar en el vídeo (ej: "cartoon, low quality")
        model: Modelo a usar (default: veo-3.1-generate-preview)
        aspect_ratio: Ratio de aspecto ("16:9" o "9:16")
        resolution: Resolución ("720p" o "1080p")
        duration_seconds: Duración en segundos (4, 6, u 8)
        image: Imagen inicial para animar (URL o base64)
        last_frame: Último frame para interpolación (URL o base64)
        reference_images: Imágenes de referencia para guiar el estilo (hasta 3)
        person_generation: Control de generación de personas
        wait_for_completion: Si True, espera a que termine. Si False, devuelve operation_name
        api_key: API key de Gemini (opcional, se obtiene de la BD)
    
    Returns:
        Dict con:
        - success: bool
        - video_url: Data URL del vídeo (data:video/mp4;base64,...)
        - video_data: Base64 del vídeo
        - mime_type: Tipo MIME
        - duration_seconds: Duración
        - model: Modelo usado
        - operation_name: ID de la operación (para tracking)
    """
    logger.info("🎬 Starting video generation", prompt=prompt[:100])
    
    # Obtener API key
    if not api_key:
        api_key = await _get_gemini_api_key()
    
    if not api_key:
        return {
            "success": False,
            "error": "No Gemini API key available. Configure it in providers or set GEMINI_API_KEY env var."
        }
    
    # Valores por defecto
    model = model or VEO_CONFIG["default_model"]
    aspect_ratio = aspect_ratio or VEO_CONFIG["default_aspect_ratio"]
    resolution = resolution or VEO_CONFIG["default_resolution"]
    duration_seconds = duration_seconds or VEO_CONFIG["default_duration"]
    
    # Validaciones
    if model not in VEO_CONFIG["models"]:
        model = VEO_CONFIG["default_model"]
    
    if aspect_ratio not in VEO_CONFIG["aspect_ratios"]:
        aspect_ratio = VEO_CONFIG["default_aspect_ratio"]
    
    if resolution not in VEO_CONFIG["resolutions"]:
        resolution = VEO_CONFIG["default_resolution"]
    
    if duration_seconds not in VEO_CONFIG["durations"]:
        duration_seconds = VEO_CONFIG["default_duration"]
    
    # Procesar imagen inicial si existe
    image_data = None
    if image:
        image_data = await _process_image_input(image)
    
    # Procesar último frame si existe
    last_frame_data = None
    if last_frame:
        last_frame_data = await _process_image_input(last_frame)
    
    # Procesar imágenes de referencia
    ref_images_data = None
    if reference_images:
        ref_images_data = []
        for ref_img in reference_images[:3]:
            data = await _process_image_input(ref_img)
            if data:
                ref_images_data.append(data)
    
    # Iniciar generación
    start_result = await _start_video_generation(
        prompt=prompt,
        model=model,
        api_key=api_key,
        negative_prompt=negative_prompt,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        duration_seconds=duration_seconds,
        image_data=image_data,
        last_frame_data=last_frame_data,
        reference_images=ref_images_data,
        person_generation=person_generation
    )
    
    if not start_result.get("success"):
        return start_result
    
    operation_name = start_result["operation_name"]
    
    # Si no queremos esperar, devolver el operation_name
    if not wait_for_completion:
        return {
            "success": True,
            "status": "processing",
            "operation_name": operation_name,
            "message": "Video generation started. Use check_video_status to poll for completion."
        }
    
    # Polling hasta completar
    poll_result = await _poll_operation(
        operation_name=operation_name,
        api_key=api_key,
        max_time=VEO_CONFIG["max_polling_time"],
        interval=VEO_CONFIG["polling_interval"]
    )
    
    if not poll_result.get("success"):
        return poll_result
    
    video_uri = poll_result.get("video_uri")
    if not video_uri:
        return {
            "success": False,
            "error": "No video URI in response"
        }
    
    # Descargar vídeo
    download_result = await _download_video(video_uri, api_key)
    
    if not download_result.get("success"):
        return download_result
    
    video_bytes = download_result["video_bytes"]
    mime_type = download_result["mime_type"]
    size_bytes = download_result.get("size_bytes", len(video_bytes))
    
    # Guardar en workspace y crear artifact
    save_result = await _save_video_as_artifact(
        video_bytes=video_bytes,
        prompt=prompt,
        provider="google",
        model=model or VEO_CONFIG["default_model"],
        mime_type=mime_type,
        duration_seconds=duration_seconds or VEO_CONFIG["default_duration"],
        aspect_ratio=aspect_ratio or VEO_CONFIG["default_aspect_ratio"],
        resolution=resolution or VEO_CONFIG["default_resolution"],
        user_id=_user_id,
    )
    
    if "error" not in save_result:
        video_url = save_result.get("local_url", f"/workspace/videos/{save_result['file_name']}")
        logger.info(
            "✅ Video generated and saved to workspace",
            model=model,
            duration=duration_seconds,
            size_kb=size_bytes // 1024,
            path=save_result.get("file_path")
        )
    else:
        # Fallback a data URL si falla el guardado
        video_b64 = base64.b64encode(video_bytes).decode("utf-8")
        video_url = f"data:{mime_type};base64,{video_b64}"
        save_result = {"error": "Failed to save to workspace"}
        logger.warning("Video saved as data URL (workspace save failed)")
    
    return {
        "success": True,
        "video_url": video_url,
        "workspace_path": save_result.get("local_url") if "error" not in save_result else None,
        "artifact_id": save_result.get("artifact_id") if "error" not in save_result else None,
        "file_name": save_result.get("file_name") if "error" not in save_result else None,
        "mime_type": mime_type,
        "duration_seconds": duration_seconds,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
        "size_bytes": size_bytes,
        "model": model,
        "operation_name": operation_name,
        "provider": "google",
        "prompt": prompt,
        "saved_to_workspace": "error" not in save_result
    }


async def _process_image_input(image_input: str) -> Optional[str]:
    """
    Procesa entrada de imagen (URL o base64) y devuelve base64.
    """
    if not image_input:
        return None
    
    # Si ya es base64 (sin prefijo data:)
    if not image_input.startswith(("http://", "https://", "data:")):
        return image_input
    
    # Si es data URL, extraer base64
    if image_input.startswith("data:"):
        try:
            _, b64_data = image_input.split(",", 1)
            return b64_data
        except:
            return None
    
    # Si es URL, descargar
    if image_input.startswith(("http://", "https://")):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(image_input)
                if response.status_code == 200:
                    return base64.b64encode(response.content).decode("utf-8")
        except Exception as e:
            logger.warning(f"Failed to download image: {e}")
    
    return None


async def check_video_status(
    operation_name: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Verifica el estado de una operación de generación de vídeo.
    
    Args:
        operation_name: Nombre de la operación devuelto por generate_video
        api_key: API key de Gemini (opcional)
    
    Returns:
        Dict con estado y vídeo si está completado
    """
    if not api_key:
        api_key = await _get_gemini_api_key()
    
    if not api_key:
        return {
            "success": False,
            "error": "No Gemini API key available"
        }
    
    base_url = "https://generativelanguage.googleapis.com/v1beta"
    url = f"{base_url}/{operation_name}"
    
    headers = {"x-goog-api-key": api_key}
    
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url, headers=headers)
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"API error: {response.status_code}"
            }
        
        data = response.json()
        
        if not data.get("done"):
            return {
                "success": True,
                "status": "processing",
                "operation_name": operation_name
            }
        
        if "error" in data:
            return {
                "success": False,
                "error": data["error"].get("message", "Unknown error")
            }
        
        # Completado - descargar vídeo
        response_data = data.get("response", {})
        video_response = response_data.get("generateVideoResponse", {})
        samples = video_response.get("generatedSamples", [])
        
        if samples:
            video_uri = samples[0].get("video", {}).get("uri")
            download_result = await _download_video(video_uri, api_key)
            
            if download_result.get("success"):
                video_bytes = download_result["video_bytes"]
                mime_type = download_result["mime_type"]
                
                # Guardar en workspace
                import uuid
                ext = "mp4" if "mp4" in mime_type else "webm"
                filename = f"video_{uuid.uuid4().hex[:12]}.{ext}"
                workspace_path = _save_video_to_workspace(video_bytes, filename, user_id=_user_id)
                
                if workspace_path:
                    video_url = f"/api/v1/workspace/files/{workspace_path}"
                else:
                    video_b64 = base64.b64encode(video_bytes).decode("utf-8")
                    video_url = f"data:{mime_type};base64,{video_b64}"
                
                return {
                    "success": True,
                    "status": "completed",
                    "video_url": video_url,
                    "workspace_path": workspace_path,
                    "mime_type": mime_type,
                    "operation_name": operation_name
                }
        
        return {
            "success": False,
            "error": "No video in completed response"
        }


async def extend_video(
    video: str,
    prompt: str,
    model: str = "veo-3.1-generate-preview",
    api_key: Optional[str] = None,
    _user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extiende un vídeo generado previamente con Veo.
    
    Args:
        video: Vídeo a extender (debe ser generado con Veo)
        prompt: Nueva descripción para la extensión
        model: Modelo a usar
        api_key: API key de Gemini
    
    Returns:
        Dict con el vídeo extendido
    """
    logger.info("🎬 Extending video", prompt=prompt[:100])
    
    if not api_key:
        api_key = await _get_gemini_api_key()
    
    if not api_key:
        return {
            "success": False,
            "error": "No Gemini API key available"
        }
    
    # Procesar vídeo de entrada
    video_data = await _process_video_input(video)
    if not video_data:
        return {
            "success": False,
            "error": "Could not process video input"
        }
    
    url = f"{VEO_CONFIG['api_url']}/{model}:predictLongRunning"
    
    payload = {
        "instances": [{
            "prompt": prompt,
            "video": {
                "bytesBase64Encoded": video_data,
                "mimeType": "video/mp4"
            }
        }],
        "parameters": {
            "resolution": "720p",
            "numberOfVideos": 1
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, json=payload, headers=headers)
        
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"API error {response.status_code}: {response.text}"
            }
        
        data = response.json()
        operation_name = data.get("name")
        
        if not operation_name:
            return {
                "success": False,
                "error": "No operation name returned"
            }
    
    # Polling
    poll_result = await _poll_operation(operation_name, api_key)
    
    if not poll_result.get("success"):
        return poll_result
    
    video_uri = poll_result.get("video_uri")
    download_result = await _download_video(video_uri, api_key)
    
    if not download_result.get("success"):
        return download_result
    
    video_bytes = download_result["video_bytes"]
    mime_type = download_result["mime_type"]
    
    # Guardar en workspace
    import uuid
    ext = "mp4" if "mp4" in mime_type else "webm"
    filename = f"video_ext_{uuid.uuid4().hex[:12]}.{ext}"
    workspace_path = _save_video_to_workspace(video_bytes, filename, user_id=_user_id)
    
    if workspace_path:
        video_url = f"/api/v1/workspace/files/{workspace_path}"
    else:
        video_b64 = base64.b64encode(video_bytes).decode("utf-8")
        video_url = f"data:{mime_type};base64,{video_b64}"
    
    return {
        "success": True,
        "video_url": video_url,
        "workspace_path": workspace_path,
        "mime_type": mime_type,
        "model": model,
        "operation_name": operation_name,
        "type": "extension"
    }


async def _process_video_input(video_input: str) -> Optional[str]:
    """Procesa entrada de vídeo y devuelve base64."""
    if not video_input:
        return None
    
    # Si ya es base64
    if not video_input.startswith(("http://", "https://", "data:")):
        return video_input
    
    # Si es data URL
    if video_input.startswith("data:"):
        try:
            _, b64_data = video_input.split(",", 1)
            return b64_data
        except:
            return None
    
    # Si es URL
    if video_input.startswith(("http://", "https://")):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(video_input)
                if response.status_code == 200:
                    return base64.b64encode(response.content).decode("utf-8")
        except Exception as e:
            logger.warning(f"Failed to download video: {e}")
    
    return None


# Tool definition para el registry
GENERATE_VIDEO_TOOL = {
    "id": "generate_video",
    "name": "generate_video",
    "description": """Genera vídeos de alta calidad usando Veo 3.1 de Google.

Capacidades:
- Text-to-video: Crea vídeos cinematográficos desde descripciones de texto
- Image-to-video: Anima imágenes existentes
- Frame interpolation: Genera vídeo entre dos frames
- Reference images: Usa hasta 3 imágenes para guiar el estilo

El prompt puede incluir:
- Diálogos entre comillas (ej: "Hello!" she said)
- Efectos de sonido (ej: tires screeching, birds chirping)
- Ambiente sonoro (ej: A faint hum in the background)
- Movimientos de cámara (ej: dolly shot, aerial view, close-up)

Ejemplos de prompts:
- "A cinematic shot of a majestic lion walking through the savannah at sunset"
- "Close-up of a woman smiling. She says 'Good morning!' with a cheerful tone"
- "Aerial drone shot over a misty mountain range at dawn, birds flying below"
""",
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Descripción detallada del vídeo. Incluye sujeto, acción, estilo, cámara y ambiente."
            },
            "negative_prompt": {
                "type": "string",
                "description": "Qué evitar en el vídeo (ej: 'cartoon, drawing, low quality')"
            },
            "model": {
                "type": "string",
                "enum": ["veo-3.1-generate-preview", "veo-3.1-fast-generate-preview"],
                "description": "Modelo a usar. 'fast' es más rápido pero menor calidad."
            },
            "aspect_ratio": {
                "type": "string",
                "enum": ["16:9", "9:16"],
                "description": "Ratio de aspecto. 16:9 horizontal, 9:16 vertical."
            },
            "resolution": {
                "type": "string",
                "enum": ["720p", "1080p"],
                "description": "Resolución del vídeo."
            },
            "duration_seconds": {
                "type": "integer",
                "enum": [4, 6, 8],
                "description": "Duración del vídeo en segundos."
            },
            "image": {
                "type": "string",
                "description": "Imagen inicial para animar (URL o base64). El vídeo partirá de esta imagen."
            },
            "last_frame": {
                "type": "string",
                "description": "Último frame para interpolación (URL o base64). Genera transición entre image y last_frame."
            }
        },
        "required": ["prompt"]
    },
    "handler": generate_video
}

EXTEND_VIDEO_TOOL = {
    "id": "extend_video",
    "name": "extend_video",
    "description": """Extiende un vídeo generado con Veo añadiendo 7 segundos más.

Solo funciona con vídeos generados previamente por Veo. Puede extender hasta 20 veces
(máximo 148 segundos total).

El prompt describe qué debe pasar en la extensión del vídeo.""",
    "parameters": {
        "type": "object",
        "properties": {
            "video": {
                "type": "string",
                "description": "Vídeo a extender (URL, base64 o data URL). Debe ser generado con Veo."
            },
            "prompt": {
                "type": "string",
                "description": "Descripción de lo que debe ocurrir en la extensión."
            }
        },
        "required": ["video", "prompt"]
    },
    "handler": extend_video
}

CHECK_VIDEO_STATUS_TOOL = {
    "id": "check_video_status",
    "name": "check_video_status", 
    "description": """Verifica el estado de una operación de generación de vídeo.

Usar cuando generate_video se llamó con wait_for_completion=False.""",
    "parameters": {
        "type": "object",
        "properties": {
            "operation_name": {
                "type": "string",
                "description": "Nombre de la operación devuelto por generate_video"
            }
        },
        "required": ["operation_name"]
    },
    "handler": check_video_status
}
