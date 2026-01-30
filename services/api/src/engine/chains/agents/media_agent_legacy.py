"""
Media Agent - Subagente especializado en generación y manipulación de imágenes

Capabilities:
- Generación de imágenes con DALL-E 3 y Stable Diffusion/Flux
- Análisis de imágenes (futuro)
- Edición de imágenes (futuro)

Este subagente recibe tareas relacionadas con imágenes del Adaptive Agent
y usa sus herramientas especializadas para completarlas.
"""

import json
import time
from typing import Optional, Dict, Any, List

import structlog

from .base_agent import BaseSubAgent, SubAgentResult
from src.tools import tool_registry
from src.tools.domains.media import generate_image
from src.engine.chains.llm_utils import call_llm_with_tools, LLMToolResponse

logger = structlog.get_logger()


MEDIA_AGENT_SYSTEM_PROMPT = """You are a specialized Media Agent focused on image generation and manipulation.

# YOUR CAPABILITIES

You have access to the following tools:
{tools_description}

# INSTRUCTIONS

1. Analyze the image generation request carefully
2. Extract key details: subject, style, colors, composition, mood
3. If the request is vague, enhance it with artistic details
4. Use the appropriate tool to generate the image
5. Return the result with the image URL

# PROMPT ENGINEERING TIPS

For better image results:
- Be specific about: subject, action, setting, lighting, style
- Include artistic direction: "digital art", "photorealistic", "watercolor", etc.
- Specify composition: "close-up", "wide shot", "centered"
- Add mood/atmosphere: "dramatic lighting", "soft colors", "vibrant"

# EXAMPLES

User: "Genera una imagen de un gato"
Enhanced prompt: "A fluffy orange tabby cat sitting on a windowsill, soft natural lighting, cozy home interior, photorealistic style"

User: "Logo para empresa de tecnología"
Enhanced prompt: "Minimalist tech company logo, abstract geometric shapes, blue and white color scheme, clean modern design, vector style"

# OUTPUT FORMAT

After generating, respond with a brief description of what was created.
"""


class MediaAgent(BaseSubAgent):
    """
    Subagente especializado en generación y manipulación de imágenes.
    
    Tools disponibles:
    - generate_image: Genera imágenes con DALL-E 3, Stable Diffusion, Flux
    
    Futuro:
    - analyze_image: Analiza contenido de imágenes
    - edit_image: Edita imágenes existentes
    """
    
    id = "media_agent"
    name = "Media Agent"
    description = "Genera y manipula imágenes usando DALL-E 3, Stable Diffusion y otros modelos"
    version = "1.0.0"
    
    domain_tools = ["generate_image"]
    
    system_prompt = MEDIA_AGENT_SYSTEM_PROMPT
    
    def __init__(self):
        super().__init__()
        self._register_domain_tools()
    
    def _register_domain_tools(self):
        """Registra las tools de dominio en el registry global."""
        from src.tools.domains.media import GENERATE_IMAGE_TOOL
        from src.tools import ToolDefinition, ToolType
        
        # Verificar si ya está registrada
        if not tool_registry.get("generate_image"):
            tool_def = ToolDefinition(
                id=GENERATE_IMAGE_TOOL["id"],
                name=GENERATE_IMAGE_TOOL["name"],
                description=GENERATE_IMAGE_TOOL["description"],
                parameters=GENERATE_IMAGE_TOOL["parameters"],
                type=ToolType.BUILTIN,
                handler=GENERATE_IMAGE_TOOL["handler"]
            )
            tool_registry.register(tool_def)
            logger.info("✅ Registered generate_image tool")
    
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
        Ejecuta una tarea de generación/manipulación de imágenes.
        
        El agente:
        1. Analiza la tarea
        2. Mejora el prompt si es necesario
        3. Genera la imagen
        4. Retorna el resultado
        """
        start_time = time.time()
        
        logger.info(
            "🎨 MediaAgent executing task",
            task=task[:100],
            has_context=bool(context)
        )
        
        # Construir mensaje con contexto
        full_task = task
        if context:
            full_task = f"{task}\n\nContext: {context}"
        
        images = []
        tools_used = []
        error = None
        
        try:
            # Opción 1: Ejecución directa si la tarea es clara
            if self._is_direct_generation_request(task):
                result = await self._direct_generate(task)
                if result.get("success"):
                    images.append({
                        "url": result.get("image_url"),
                        "prompt": result.get("prompt"),
                        "revised_prompt": result.get("revised_prompt"),
                        "provider": result.get("provider"),
                        "model": result.get("model")
                    })
                    tools_used.append("generate_image")
                    
                    response = self._build_response(result)
                    
                    return SubAgentResult(
                        success=True,
                        response=response,
                        agent_id=self.id,
                        agent_name=self.name,
                        tools_used=tools_used,
                        images=images,
                        data=result,
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )
                else:
                    error = result.get("error", "Unknown error")
            
            # Opción 2: Usar LLM para analizar y mejorar prompt
            if llm_url and model:
                result = await self._llm_assisted_generate(
                    task=full_task,
                    llm_url=llm_url,
                    model=model,
                    provider_type=provider_type,
                    api_key=api_key
                )
                
                if result.get("success"):
                    images.append({
                        "url": result.get("image_url"),
                        "prompt": result.get("prompt"),
                        "revised_prompt": result.get("revised_prompt"),
                        "provider": result.get("provider"),
                        "model": result.get("model")
                    })
                    tools_used.append("generate_image")
                    
                    response = self._build_response(result)
                    
                    return SubAgentResult(
                        success=True,
                        response=response,
                        agent_id=self.id,
                        agent_name=self.name,
                        tools_used=tools_used,
                        images=images,
                        data=result,
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )
                else:
                    error = result.get("error", "Unknown error")
            
            # Si llegamos aquí, algo falló
            return SubAgentResult(
                success=False,
                response=f"Error generando imagen: {error}",
                agent_id=self.id,
                agent_name=self.name,
                error=error,
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
    
    def _is_direct_generation_request(self, task: str) -> bool:
        """Detecta si la tarea es una solicitud directa de generación."""
        task_lower = task.lower()
        direct_patterns = [
            "genera una imagen",
            "generate an image",
            "crea una imagen",
            "create an image",
            "dibuja",
            "draw",
            "genera un logo",
            "create a logo"
        ]
        return any(pattern in task_lower for pattern in direct_patterns)
    
    async def _direct_generate(self, task: str) -> Dict[str, Any]:
        """
        Generación directa: extrae el prompt de la tarea y genera.
        """
        # Extraer el prompt de la tarea
        # Patrones comunes: "genera una imagen de X", "crea X"
        prompt = task
        
        # Limpiar prefijos comunes
        prefixes = [
            "genera una imagen de ",
            "generate an image of ",
            "crea una imagen de ",
            "create an image of ",
            "dibuja ",
            "draw "
        ]
        
        for prefix in prefixes:
            if prompt.lower().startswith(prefix):
                prompt = prompt[len(prefix):]
                break
        
        # Generar la imagen
        return await generate_image(prompt=prompt)
    
    async def _llm_assisted_generate(
        self,
        task: str,
        llm_url: str,
        model: str,
        provider_type: str,
        api_key: Optional[str]
    ) -> Dict[str, Any]:
        """
        Usa el LLM para analizar la tarea y mejorar el prompt antes de generar.
        """
        # Construir prompt de análisis
        analysis_prompt = f"""Analyze this image generation request and create an optimal prompt:

REQUEST: {task}

Create a detailed image generation prompt that includes:
1. Main subject with specific details
2. Art style (photorealistic, digital art, watercolor, etc.)
3. Lighting and atmosphere
4. Composition details
5. Color palette if relevant

Respond with ONLY the enhanced prompt text, nothing else."""

        messages = [
            {"role": "system", "content": "You are an expert at creating detailed image generation prompts."},
            {"role": "user", "content": analysis_prompt}
        ]
        
        try:
            from ..llm_utils import call_llm
            
            enhanced_prompt = await call_llm(
                llm_url=llm_url,
                model=model,
                messages=messages,
                temperature=0.7,
                provider_type=provider_type,
                api_key=api_key
            )
            
            # Limpiar el prompt
            enhanced_prompt = enhanced_prompt.strip().strip('"').strip("'")
            
            logger.info(
                "🎨 Enhanced prompt generated",
                original=task[:50],
                enhanced=enhanced_prompt[:100]
            )
            
            # Generar con el prompt mejorado
            return await generate_image(prompt=enhanced_prompt)
            
        except Exception as e:
            logger.warning(f"LLM enhancement failed, using original: {e}")
            # Fallback a generación directa
            return await self._direct_generate(task)
    
    def _build_response(self, result: Dict[str, Any]) -> str:
        """Construye la respuesta textual del agente."""
        if not result.get("success"):
            return f"No se pudo generar la imagen: {result.get('error')}"
        
        parts = ["He generado la imagen solicitada."]
        
        if result.get("revised_prompt"):
            parts.append(f"\n\n**Prompt usado:** {result['revised_prompt']}")
        
        if result.get("image_url"):
            parts.append(f"\n\n![Imagen generada]({result['image_url']})")
        
        parts.append(f"\n\n*Generada con {result.get('provider', 'AI')} ({result.get('model', 'default')})*")
        
        return "".join(parts)
