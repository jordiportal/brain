"""
Designer Agent - Subagente de diseño visual.

Patrón: LLM-Only con Tools
Genera imágenes, vídeos y presentaciones usando LLM con herramientas.
"""

import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

import structlog

from ..base import BaseSubAgent, SubAgentResult, Skill
from ...llm_utils import call_llm_with_tools

logger = structlog.get_logger()


def _read_system_prompt() -> str:
    """Lee el prompt desde fichero."""
    path = Path(__file__).parent / "prompts" / "system_prompt.txt"
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return """Eres un diseñador visual experto. Genera imágenes, vídeos y presentaciones profesionales.

Herramientas disponibles:
- generate_image: Genera imágenes (logos, ilustraciones, fotos)
- generate_video: Genera vídeos cinematográficos con Veo 3.1
- generate_slides: Genera presentaciones HTML profesionales
- analyze_image: Analiza imágenes para verificar calidad

Tienes acceso a herramientas de filesystem para guardar archivos.
Usa las herramientas según la necesidad del usuario."""


# Skills simplificados para Designer
DESIGNER_SKILLS = [
    Skill(
        id="design",
        name="Diseño Visual",
        description="Generación de imágenes, vídeos y presentaciones profesionales con IA"
    ),
    Skill(
        id="slides",
        name="Presentaciones",
        description="Diseño de slides HTML/CSS modernos con templates profesionales"
    )
]


class DesignerAgent(BaseSubAgent):
    """Subagente de diseño: imágenes, vídeos y presentaciones."""

    id = "designer_agent"
    name = "Designer"
    description = "Diseñador visual: imágenes, vídeos, presentaciones, logos"
    version = "3.0.0"
    domain_tools = ["generate_image", "edit_image", "generate_video", "generate_slides", "analyze_image"]
    available_skills = DESIGNER_SKILLS

    role = "Diseñador Visual"
    expertise = "Experto en diseño visual: generación de imágenes, vídeos cinematográficos y presentaciones profesionales"
    task_requirements = "Describe la tarea: imagen, vídeo, presentación, o cualquier combinación"

    def __init__(self):
        super().__init__()
        self.system_prompt = _read_system_prompt()
        logger.info(f"🎨 DesignerAgent initialized")

    async def execute(
        self,
        task: str,
        context: Optional[str] = None,
        llm_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_type: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> SubAgentResult:
        """Ejecuta usando LLM con herramientas."""
        start_time = time.time()
        logger.info("🎨 DesignerAgent executing", task=task[:100])

        # Validar LLM configurado
        if not llm_url or not model or not provider_type:
            return SubAgentResult(
                success=False,
                response="❌ **Error:** Se requiere configuración LLM completa para este agente (URL, modelo y tipo de proveedor).\n\nPor favor, configure un modelo LLM en la sección de Configuración del subagente.",
                agent_id=self.id,
                agent_name=self.name,
                error="LLM_NOT_CONFIGURED",
                execution_time_ms=0
            )

        try:
            return await self._execute_with_llm(
                task, context, llm_url, model, provider_type, api_key, start_time
            )
        except Exception as e:
            logger.error(f"DesignerAgent error: {e}", exc_info=True)
            return SubAgentResult(
                success=False,
                response=f"❌ **Error en diseño:** {str(e)}",
                agent_id=self.id,
                agent_name=self.name,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

    async def _execute_with_llm(
        self,
        task: str,
        context: Optional[str],
        llm_url: str,
        model: str,
        provider_type: str,
        api_key: Optional[str],
        start_time: float
    ) -> SubAgentResult:
        """Ejecuta con LLM que decide qué herramientas usar."""
        
        # Obtener herramientas disponibles
        tools = self.get_tools()
        
        # Construir mensajes
        system_content = self.system_prompt + self.get_skills_for_prompt()
        user_content = f"Tarea: {task}"
        if context:
            user_content += f"\n\nContexto adicional: {context}"
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]
        
        # Llamar LLM con herramientas
        response = await call_llm_with_tools(
            messages=messages,
            tools=[tool.to_function_schema() for tool in tools],
            temperature=0.7,
            provider_type=provider_type,
            api_key=api_key,
            llm_url=llm_url,
            model=model
        )
        
        # Si no hay tool calls, retornar respuesta directa
        if not response.tool_calls:
            return SubAgentResult(
                success=True,
                response=response.content or "No se pudo generar respuesta",
                agent_id=self.id,
                agent_name=self.name,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        
        # Ejecutar tool calls y recolectar resultados
        import json
        tools_used = []
        images = []
        videos = []
        tool_results = []
        
        for tc in response.tool_calls:
            tool_name = tc.function.get("name", "")
            tool_params_raw = tc.function.get("arguments", {})
            
            # Parsear argumentos si vienen como string JSON
            if isinstance(tool_params_raw, str):
                try:
                    tool_params = json.loads(tool_params_raw)
                except json.JSONDecodeError:
                    tool_params = {}
            else:
                tool_params = tool_params_raw or {}
            
            tools_used.append(tool_name)
            
            try:
                # Buscar y ejecutar la tool
                tool = next((t for t in tools if t.id == tool_name or t.name == tool_name), None)
                if tool and tool.handler:
                    logger.info(f"🛠️ Executing tool: {tool_name}", params=tool_params)
                    result = await tool.handler(**tool_params)
                    tool_results.append({"tool": tool_name, "result": result})
                    
                    # Extraer imágenes del resultado
                    if isinstance(result, dict):
                        if result.get("success") and result.get("image_base64"):
                            images.append({
                                "url": result.get("image_url", ""),
                                "base64": result.get("image_base64"),
                                "mime_type": "image/png",
                                "artifact_id": result.get("artifact_id")
                            })
                        if result.get("success") and result.get("video_url"):
                            videos.append({
                                "url": result.get("video_url"),
                                "mime_type": "video/mp4",
                                "artifact_id": result.get("artifact_id")
                            })
                    
                    logger.info(f"✅ Tool {tool_name} executed successfully")
                else:
                    logger.warning(f"⚠️ Tool {tool_name} not found or no handler")
            except Exception as e:
                logger.error(f"❌ Error executing tool {tool_name}: {e}")
                tool_results.append({"tool": tool_name, "error": str(e)})
        
        # Construir mensaje de respuesta
        if images:
            response_text = f"✅ Imagen generada exitosamente.\n\nTareas completadas: {', '.join(tools_used)}"
        elif videos:
            response_text = f"✅ Vídeo generado exitosamente.\n\nTareas completadas: {', '.join(tools_used)}"
        else:
            response_text = response.content or f"Ejecutadas herramientas: {', '.join(tools_used)}"
        
        return SubAgentResult(
            success=True,
            response=response_text,
            agent_id=self.id,
            agent_name=self.name,
            tools_used=tools_used,
            images=images,
            videos=videos,
            data={"tool_results": tool_results} if tool_results else {},
            execution_time_ms=int((time.time() - start_time) * 1000)
        )


# Instancia para registro
designer_agent = DesignerAgent()
