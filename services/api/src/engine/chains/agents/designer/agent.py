"""
Designer Agent - Subagente de diseño visual.

Usa el mismo bucle iterativo que el agente principal (run_session_loop).
Genera imágenes, vídeos y presentaciones usando tools del dominio.
"""

import time
from pathlib import Path
from typing import Optional

import structlog

from ..base import BaseSubAgent, SubAgentResult, Skill

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
        logger.info("🎨 DesignerAgent initialized (shared loop)")

    async def execute(
        self,
        task: str,
        context: Optional[str] = None,
        session_id: Optional[str] = None,
        llm_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_type: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> SubAgentResult:
        """Ejecuta usando el bucle compartido (run_session_loop)."""
        start_time = time.time()
        logger.info("🎨 DesignerAgent executing", task=task[:100])
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
            return await super().execute(
                task=task,
                context=context,
                session_id=session_id,
                llm_url=llm_url,
                model=model,
                provider_type=provider_type,
                api_key=api_key,
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


# Instancia para registro
designer_agent = DesignerAgent()
