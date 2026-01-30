"""
Media Agent - Subagente para generación de imágenes.

Usa DALL-E 3, Stable Diffusion, Flux para crear imágenes.
"""

import time
from typing import Optional, Dict, Any

import structlog

from ..base import BaseSubAgent, SubAgentResult
from .prompts import SYSTEM_PROMPT

logger = structlog.get_logger()


class MediaAgent(BaseSubAgent):
    """Subagente para generación de imágenes."""
    
    id = "media_agent"
    name = "Media Agent"
    description = "Genera imágenes con DALL-E 3, Stable Diffusion, Flux"
    version = "2.0.0"
    domain_tools = ["generate_image"]
    system_prompt = SYSTEM_PROMPT
    
    task_requirements = """Envíame una descripción detallada de la imagen a generar.

FORMATO: Texto descriptivo con:
- Sujeto principal (qué aparece)
- Estilo visual (realista, ilustración, 3D, minimalista, etc.)
- Colores o paleta (opcional)
- Composición (primer plano, paisaje, etc.)
- Ambiente/mood (profesional, alegre, dramático, etc.)

EJEMPLOS:
- "Logo minimalista para empresa de tecnología, colores azul y blanco, estilo limpio"
- "Ilustración de un gato naranja sentado en una ventana, estilo acuarela, luz cálida"
- "Foto realista de montañas nevadas al atardecer, colores dramáticos"

NO necesitas especificar el modelo ni parámetros técnicos, yo los selecciono."""
    
    # Patrones de solicitud directa
    DIRECT_PATTERNS = [
        "genera una imagen", "generate an image",
        "crea una imagen", "create an image",
        "dibuja", "draw", "genera un logo", "create a logo"
    ]
    
    # Prefijos a limpiar del prompt
    PROMPT_PREFIXES = [
        "genera una imagen de ", "generate an image of ",
        "crea una imagen de ", "create an image of ",
        "dibuja ", "draw "
    ]
    
    def __init__(self):
        super().__init__()
        # NO registramos generate_image en el registry global
        # El subagente la usa internamente via import directo
    
    async def execute(
        self,
        task: str,
        context: Optional[str] = None,
        llm_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_type: str = "ollama",
        api_key: Optional[str] = None
    ) -> SubAgentResult:
        """Ejecuta generación de imagen."""
        start_time = time.time()
        
        logger.info("🎨 MediaAgent executing", task=task[:100])
        
        try:
            # Determinar el prompt
            if self._is_direct_request(task):
                result = await self._generate_direct(task)
            elif llm_url and model:
                result = await self._generate_with_llm(
                    task, llm_url, model, provider_type, api_key
                )
            else:
                result = await self._generate_direct(task)
            
            if result.get("success"):
                images = [{
                    "url": result.get("image_url"),
                    "prompt": result.get("prompt"),
                    "revised_prompt": result.get("revised_prompt"),
                    "provider": result.get("provider"),
                    "model": result.get("model")
                }]
                
                return SubAgentResult(
                    success=True,
                    response=self._build_response(result),
                    agent_id=self.id,
                    agent_name=self.name,
                    tools_used=["generate_image"],
                    images=images,
                    data=result,
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
            else:
                return SubAgentResult(
                    success=False,
                    response=f"Error: {result.get('error', 'Unknown')}",
                    agent_id=self.id,
                    agent_name=self.name,
                    error=result.get("error"),
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
                
        except Exception as e:
            logger.error(f"MediaAgent error: {e}", exc_info=True)
            return SubAgentResult(
                success=False,
                response=f"Error: {str(e)}",
                agent_id=self.id,
                agent_name=self.name,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
    
    def _is_direct_request(self, task: str) -> bool:
        """Detecta si es solicitud directa."""
        task_lower = task.lower()
        return any(p in task_lower for p in self.DIRECT_PATTERNS)
    
    async def _generate_direct(self, task: str) -> Dict[str, Any]:
        """Generación directa sin LLM."""
        from src.tools.domains.media import generate_image
        
        prompt = task
        for prefix in self.PROMPT_PREFIXES:
            if prompt.lower().startswith(prefix):
                prompt = prompt[len(prefix):]
                break
        
        return await generate_image(prompt=prompt)
    
    async def _generate_with_llm(
        self,
        task: str,
        llm_url: str,
        model: str,
        provider_type: str,
        api_key: Optional[str]
    ) -> Dict[str, Any]:
        """Genera con prompt mejorado por LLM."""
        from src.tools.domains.media import generate_image
        from ...llm_utils import call_llm
        
        messages = [
            {"role": "system", "content": "Create an enhanced image prompt. Output ONLY the prompt."},
            {"role": "user", "content": f"Enhance this for image generation: {task}"}
        ]
        
        try:
            enhanced = await call_llm(
                llm_url=llm_url,
                model=model,
                messages=messages,
                temperature=0.7,
                provider_type=provider_type,
                api_key=api_key
            )
            enhanced = enhanced.strip().strip('"\'')
            logger.info("🎨 Enhanced prompt", original=task[:50], enhanced=enhanced[:100])
            return await generate_image(prompt=enhanced)
        except Exception as e:
            logger.warning(f"LLM enhancement failed: {e}")
            return await self._generate_direct(task)
    
    def _build_response(self, result: Dict[str, Any]) -> str:
        """Construye respuesta textual."""
        if not result.get("success"):
            return f"No se pudo generar: {result.get('error')}"
        
        parts = ["He generado la imagen solicitada."]
        
        if result.get("revised_prompt"):
            parts.append(f"\n\n**Prompt:** {result['revised_prompt']}")
        
        if result.get("image_url"):
            parts.append(f"\n\n![Imagen]({result['image_url']})")
        
        parts.append(f"\n\n*{result.get('provider', 'AI')} ({result.get('model', 'default')})*")
        
        return "".join(parts)
