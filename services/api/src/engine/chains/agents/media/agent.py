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
    description = "Director de arte especializado en generación de imágenes"
    version = "2.1.0"
    domain_tools = ["generate_image"]
    system_prompt = SYSTEM_PROMPT
    
    # Rol y expertise
    role = "Director de Arte Digital"
    expertise = """Soy director de arte especializado en generación de imágenes con IA.

Puedo ayudarte con:
- Elegir el estilo visual adecuado (realista, ilustración, 3D, minimalista, etc.)
- Definir la composición y encuadre de la imagen
- Sugerir paletas de colores que transmitan el mensaje
- Decidir entre diferentes modelos de IA según el resultado deseado
- Optimizar el prompt para mejores resultados

Cuando me consultes, te daré recomendaciones artísticas antes de generar."""

    task_requirements = """## MODOS DE USO

### Modo Consulta (recomendado para proyectos importantes)
Envía: {"mode": "consult", "concept": "descripción", "purpose": "uso"}
→ Te daré recomendaciones de estilo y composición

### Modo Ejecución (directo)
Envía descripción de la imagen con:
- Sujeto principal
- Estilo visual (realista, ilustración, 3D, minimalista)
- Paleta de colores (opcional)
- Composición y mood

EJEMPLOS:
- "Logo minimalista tech, colores azul y blanco"
- "Ilustración acuarela de gato naranja en ventana, luz cálida"
- "Foto realista de montañas nevadas al atardecer"
"""
    
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
        """
        Ejecuta generación de imagen.
        
        Soporta dos modos:
        - consult: Devuelve recomendaciones artísticas
        - execute: Genera la imagen
        """
        import json
        start_time = time.time()
        
        # Detectar modo consulta
        try:
            task_data = json.loads(task)
            if task_data.get("mode") == "consult":
                logger.info("🎨 MediaAgent consulting", concept=task_data.get("concept", "")[:50])
                return await self._handle_consult(task_data, llm_url, model, provider_type, api_key)
        except (json.JSONDecodeError, TypeError):
            pass  # No es JSON, proceder con ejecución normal
        
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
    
    async def _handle_consult(
        self,
        task_data: Dict[str, Any],
        llm_url: Optional[str],
        model: Optional[str],
        provider_type: str,
        api_key: Optional[str]
    ) -> SubAgentResult:
        """
        Modo consulta: da recomendaciones artísticas antes de generar.
        """
        from ...llm_utils import call_llm_with_tools
        
        concept = task_data.get("concept", "")
        purpose = task_data.get("purpose", "general")
        style_preference = task_data.get("style", "")
        
        consult_prompt = f"""Eres un Director de Arte Digital con experiencia en generación de imágenes con IA.

Un colega te pide ayuda para crear una imagen:

**CONCEPTO:** {concept}
**USO:** {purpose}
{f"**PREFERENCIA DE ESTILO:** {style_preference}" if style_preference else ""}

Dame tus recomendaciones artísticas de forma concisa:

1. **Estilo Visual** - ¿Qué estilo funcionaría mejor? (fotorrealista, ilustración, 3D, flat design, etc.)

2. **Composición** - ¿Cómo encuadrarías la imagen? (primer plano, plano general, ángulo, etc.)

3. **Paleta de Colores** - ¿Qué colores transmitirían mejor el mensaje?

4. **Modelo Recomendado** - ¿DALL-E 3 (detallado, creativo) o Stable Diffusion (estilizado)?

5. **Prompt Sugerido** - Propón el prompt que usarías

Sé conciso y profesional."""

        try:
            if not llm_url or not api_key:
                return SubAgentResult(
                    success=True,
                    response=f"""🎨 **Recomendaciones para "{concept}"**

**Estilo:** Te sugiero un estilo que se adapte al uso ({purpose}).

**Composición:** Dependiendo del concepto, considera:
- Primer plano para impacto y detalle
- Plano general para contexto
- Ángulo dramático para dinamismo

**Prompt base sugerido:** "{concept}, high quality, professional"

¿Quieres que proceda con esta dirección o tienes preferencias específicas?""",
                    agent_id=self.id,
                    agent_name=self.name,
                    data={"mode": "consult", "concept": concept, "ready_for_execution": True}
                )
            
            response = await call_llm_with_tools(
                messages=[
                    {"role": "system", "content": "Eres un director de arte experto. Responde de forma concisa y profesional en español."},
                    {"role": "user", "content": consult_prompt}
                ],
                tools=[],
                temperature=0.7,
                provider_type=provider_type,
                api_key=api_key,
                llm_url=llm_url,
                model=model
            )
            
            return SubAgentResult(
                success=True,
                response=response.content or "Sin recomendaciones",
                agent_id=self.id,
                agent_name=self.name,
                data={"mode": "consult", "concept": concept, "ready_for_execution": True}
            )
            
        except Exception as e:
            logger.error(f"Consult error: {e}")
            return SubAgentResult(
                success=False,
                response=f"Error en consulta: {str(e)}",
                agent_id=self.id,
                agent_name=self.name,
                error=str(e)
            )
