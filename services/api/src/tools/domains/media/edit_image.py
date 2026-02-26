"""
Edit Image Tool - Edición de imágenes con IA usando Gemini

Proveedores soportados:
- gemini: Gemini 2.5 Flash Image - soporta edición de imágenes
  Referencia: https://ai.google.dev/gemini-api/docs/image-generation
  
El tool permite:
1. Editar una imagen existente referenciada por su artifact_id (@img_xxx)
2. Subir una nueva imagen y editarla
3. Múltiples tipos de edición: transformaciones, blending, inpainting, etc.
"""

import os
import base64
import httpx
import structlog
from typing import Dict, Any, Optional, Literal
from datetime import datetime
from pathlib import Path

logger = structlog.get_logger()

# Workspace path for storing edited images
WORKSPACE_PATH = Path("/workspace/images")


async def _save_edited_image(
    image_data: bytes,
    original_artifact_id: str,
    prompt: str,
    provider: str,
    model: str,
    mime_type: str = "image/png",
    conversation_id: Optional[str] = None,
    agent_id: Optional[str] = "designer_agent",
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Guarda la imagen editada en el workspace y registra como artifact.
    
    Returns:
        Dict con file_path, file_name, image_url (local), artifact_id
    """
    try:
        # Asegurar que el directorio existe
        WORKSPACE_PATH.mkdir(parents=True, exist_ok=True)
        
        # Generar nombre de archivo único
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_prompt = prompt[:30].replace(' ', '_').replace('/', '_').replace('\\', '_')
        file_name = f"edited_{provider}_{safe_prompt}_{timestamp}.png"
        file_path = WORKSPACE_PATH / file_name
        
        # Guardar archivo
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        file_size = len(image_data)
        
        # Determinar dimensiones si es posible
        width, height = None, None
        try:
            from PIL import Image as PILImage
            with PILImage.open(file_path) as img:
                width, height = img.size
        except Exception:
            pass  # No es crítico
        
        # Crear registro en artifacts
        try:
            from src.artifacts import ArtifactRepository, ArtifactCreate, ArtifactType
            
            artifact_data = ArtifactCreate(
                type=ArtifactType.IMAGE,
                title=f"Imagen editada: {prompt[:50]}...",
                description=prompt,
                file_path=f"/workspace/images/{file_name}",
                file_name=file_name,
                mime_type=mime_type,
                file_size=file_size,
                conversation_id=conversation_id,
                agent_id=agent_id,
                tool_id="edit_image",
                metadata={
                    "width": width,
                    "height": height,
                    "provider": provider,
                    "model": model,
                    "prompt": prompt,
                    "original_artifact_id": original_artifact_id,
                    "edited": True
                }
            )
            
            artifact = await ArtifactRepository.create(user_id or "default", artifact_data)
            
            if artifact:
                logger.info(
                    f"✅ Edited image saved and artifact created: {artifact.artifact_id}",
                    file_path=str(file_path),
                    file_size=file_size,
                    original_artifact_id=original_artifact_id
                )
                
                return {
                    "file_path": str(file_path),
                    "file_name": file_name,
                    "local_url": f"/workspace/images/{file_name}",
                    "artifact_id": artifact.artifact_id,
                    "file_size": file_size,
                    "width": width,
                    "height": height
                }
        except Exception as e:
            logger.error(f"Error creating artifact record: {e}")
            # Continuar sin registro de artifact si falla
        
        return {
            "file_path": str(file_path),
            "file_name": file_name,
            "local_url": f"/workspace/images/{file_name}",
            "file_size": file_size
        }
        
    except Exception as e:
        logger.error(f"Error saving edited image to workspace: {e}")
        return {"error": str(e)}


async def _get_gemini_api_key() -> Optional[str]:
    """Obtiene la API key de Gemini desde la BD o variables de entorno"""
    
    # Primero intentar desde la BD (providers)
    try:
        from src.providers.llm_provider import get_provider_by_type
        
        gemini_provider = await get_provider_by_type("gemini")
        if gemini_provider and gemini_provider.api_key:
            logger.debug("Gemini API key loaded from database for image editing")
            return gemini_provider.api_key
    except Exception as e:
        logger.warning(f"Could not load Gemini provider from database: {e}")
    
    # Fallback a variable de entorno
    env_key = os.getenv("GEMINI_API_KEY")
    if env_key:
        logger.debug("Gemini API key loaded from environment")
        return env_key
    
    return None


async def _load_image_from_artifact(artifact_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Carga una imagen desde un artifact existente.
    
    Args:
        artifact_id: ID del artifact (ej: @img_abc123 o img_abc123)
    
    Returns:
        Dict con image_data (bytes), mime_type, artifact_id o None si no se encuentra
    """
    try:
        # Limpiar el ID (quitar prefijo @ si existe)
        clean_id = artifact_id.lstrip('@')
        
        from src.artifacts import ArtifactRepository
        
        artifact = await ArtifactRepository.get_by_id(user_id or "default", clean_id)
        
        if not artifact:
            logger.warning(f"Artifact not found: {clean_id}")
            return None
        
        if artifact.type != "image":
            logger.warning(f"Artifact {clean_id} is not an image (type: {artifact.type})")
            return None
        
        # Leer el archivo de imagen
        file_path = Path(artifact.file_path)
        if not file_path.exists():
            logger.error(f"Image file not found: {file_path}")
            return None
        
        with open(file_path, 'rb') as f:
            image_data = f.read()
        
        logger.info(
            f"✅ Image loaded from artifact: {clean_id}",
            file_path=str(file_path),
            file_size=len(image_data)
        )
        
        return {
            "image_data": image_data,
            "mime_type": artifact.mime_type or "image/png",
            "artifact_id": clean_id,
            "file_path": str(file_path),
            "width": artifact.metadata.get("width") if artifact.metadata else None,
            "height": artifact.metadata.get("height") if artifact.metadata else None
        }
        
    except Exception as e:
        logger.error(f"Error loading image from artifact: {e}", exc_info=True)
        return None


async def _edit_with_gemini(
    image_data: bytes,
    prompt: str,
    model: str = "gemini-2.5-flash-image",
    mime_type: str = "image/png"
) -> Dict[str, Any]:
    """
    Edita una imagen con Gemini 2.5 Flash Image.
    
    Documentación:
    - Gemini soporta edición multi-turn (ediciones secuenciales)
    - Puede hacer transformaciones naturales con lenguaje
    - Soporta blend de múltiples imágenes
    
    Args:
        image_data: Bytes de la imagen original
        prompt: Instrucciones de edición
        model: Modelo Gemini a usar
        mime_type: Tipo MIME de la imagen
    
    Returns:
        Dict con la imagen editada
    """
    
    api_key = await _get_gemini_api_key()
    if not api_key:
        return {
            "success": False,
            "error": "GEMINI_API_KEY no configurada. Configure en Providers (tipo: gemini) o en variable de entorno."
        }
    
    # Codificar imagen en base64
    image_b64 = base64.b64encode(image_data).decode('utf-8')
    
    # Construir el payload según la API de Gemini para edición
    # La API espera: prompt de texto + imagen como input
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": image_b64
                    }
                }
            ]
        }],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"]
        }
    }
    
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
        
        # Extraer la imagen editada de la respuesta
        result = {
            "success": True,
            "prompt": prompt,
            "provider": "gemini",
            "model": model
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
                    result["image_url"] = data_url
                    result["image_base64"] = image_b64
                    result["mime_type"] = mime_type
        
        if not result.get("image_url"):
            return {
                "success": False,
                "error": "No se generó imagen editada en la respuesta",
                "raw_response": data
            }
        
        logger.info(
            "✅ Image edited with Gemini",
            model=model,
            has_url=bool(result.get("image_url"))
        )
        
        return result


async def edit_image(
    artifact_id: str,
    prompt: str,
    model: str = "gemini-2.5-flash-image",
    provider: Literal["gemini", "auto"] = "auto",
    _user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Edita una imagen existente usando IA.
    
    Esta herramienta permite modificar imágenes generadas anteriormente o subidas por el usuario.
    Referencia la imagen usando su artifact_id (ej: @img_abc123 o img_abc123).
    
    Args:
        artifact_id: ID del artifact a editar (con o sin prefijo @)
        prompt: Instrucciones detalladas de la edición
                Ejemplos:
                - "Cambia el fondo a azul cielo"
                - "Añade un gato negro en la esquina inferior derecha"
                - "Convierte a estilo anime"
                - "Haz que sea más brillante y colorido"
                - "Cambia el atuendo de la persona a traje formal"
        model: Modelo a usar (solo Gemini soporta edición actualmente)
               - gemini-2.5-flash-image: Rápido y eficiente
               - gemini-3-pro-image-preview: Mayor calidad
        provider: Proveedor (solo 'gemini' soporta edición por ahora)
    
    Returns:
        Dict con:
        - success: bool
        - image_url: URL de la imagen editada
        - artifact_id: ID del nuevo artifact creado
        - prompt: Prompt usado
        - original_artifact_id: ID del artifact original
        - text_response: Descripción opcional de la edición realizada
    
    Examples:
        >>> await edit_image("@img_abc123", "Cambia el fondo a un atardecer")
        >>> await edit_image("img_abc123", "Convierte a estilo anime japones")
        >>> await edit_image("@img_xyz789", "Añade un logo en la esquina superior")
    """
    
    logger.info(
        "🎨 Editing image",
        artifact_id=artifact_id,
        prompt=prompt[:100],
        provider=provider,
        model=model
    )
    
    # Validar que tenemos API key de Gemini
    if provider == "auto":
        gemini_key = await _get_gemini_api_key()
        if gemini_key:
            provider = "gemini"
        else:
            return {
                "success": False,
                "error": "No hay API key de Gemini configurada para edición de imágenes. Configure GEMINI_API_KEY en Providers."
            }
    
    # Cargar la imagen desde el artifact
    image_info = await _load_image_from_artifact(artifact_id, user_id=_user_id)
    
    if not image_info:
        return {
            "success": False,
            "error": f"No se pudo cargar la imagen con artifact_id: {artifact_id}. Verifica que el ID sea correcto y sea una imagen."
        }
    
    try:
        # Editar la imagen según el proveedor
        if provider == "gemini":
            result = await _edit_with_gemini(
                image_data=image_info["image_data"],
                prompt=prompt,
                model=model,
                mime_type=image_info["mime_type"]
            )
        else:
            return {
                "success": False,
                "error": f"Proveedor no soportado para edición: {provider}. Solo Gemini soporta edición de imágenes.",
                "available_providers": ["gemini"]
            }
        
        # Si la edición falló, retornar error
        if not result.get("success"):
            return result
        
        # Guardar la imagen editada en el workspace y crear artifact
        if result.get("image_base64"):
            # Viene como base64 (Gemini)
            image_data = base64.b64decode(result["image_base64"])
            mime_type = result.get("mime_type", "image/png")
            
            # Guardar en workspace y crear artifact
            save_result = await _save_edited_image(
                image_data=image_data,
                original_artifact_id=image_info["artifact_id"],
                prompt=prompt,
                provider=provider,
                model=result.get("model", model),
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
                    "original_artifact_id": image_info["artifact_id"],
                    "width": save_result.get("width"),
                    "height": save_result.get("height"),
                    "saved_to_workspace": True
                })
        
        return result
        
    except Exception as e:
        logger.error(f"Error editing image: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "provider": provider,
            "original_artifact_id": image_info["artifact_id"],
            "prompt": prompt
        }


# ============================================
# Tool Definition para el Registry
# ============================================

EDIT_IMAGE_TOOL = {
    "id": "edit_image",
    "name": "edit_image",
    "description": """Edita una imagen existente usando IA generativa (Gemini 2.5 Flash Image).

Esta herramienta permite modificar imágenes generadas previamente o subidas por el usuario.
Referencia la imagen usando su ID de artefacto (ej: @img_abc123 o img_abc123).

Tipos de ediciones soportadas:
- Cambios de fondo: "Cambia el fondo a azul cielo", "Pon un paisaje montañoso detrás"
- Modificaciones de objetos: "Añade un gato negro", "Elimina la persona de la derecha"
- Cambios de estilo: "Convierte a estilo anime", "Haz que parezca una pintura al óleo"
- Ajustes de color: "Hazlo más brillante", "Aumenta el contraste", "Convierte a blanco y negro"
- Modificaciones de personas: "Cambia el atuendo a traje formal", "Sonríe a la persona"
- Composición: "Zoom en el rostro", "Mueve el objeto a la izquierda"

Para usar:
1. Copia el ID de la imagen (botón "Copiar ID" en el visor de artefactos)
2. Menciona el ID en tu mensaje: "Edita @img_abc123 para que tenga fondo azul"
3. El sistema cargará la imagen y aplicará la edición solicitada

Nota: Actualmente solo Gemini (gemini-2.5-flash-image) soporta edición de imágenes.""",
    "parameters": {
        "type": "object",
        "properties": {
            "artifact_id": {
                "type": "string",
                "description": "ID del artefacto a editar. Puede incluir prefijo @ (ej: @img_abc123) o sin él (ej: img_abc123). Copia el ID desde el visor de artefactos."
            },
            "prompt": {
                "type": "string",
                "description": "Instrucciones detalladas de la edición a realizar. Sea específico: 'Cambia el fondo a azul cielo', 'Convierte a estilo anime', 'Añade un logo en la esquina superior derecha', etc."
            },
            "model": {
                "type": "string",
                "enum": ["gemini-2.5-flash-image", "gemini-3-pro-image-preview"],
                "default": "gemini-2.5-flash-image",
                "description": "Modelo Gemini para edición. gemini-2.5-flash-image es rápido, gemini-3-pro-image-preview tiene mejor calidad."
            },
            "provider": {
                "type": "string",
                "enum": ["gemini", "auto"],
                "default": "auto",
                "description": "Proveedor. Solo Gemini soporta edición actualmente. 'auto' seleccionará Gemini si hay API key disponible."
            }
        },
        "required": ["artifact_id", "prompt"]
    },
    "handler": edit_image
}
