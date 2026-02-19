"""
Researcher Agent - Búsqueda e investigación en internet.

Usa el mismo bucle iterativo que el agente principal (run_session_loop).
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
        return """Eres un investigador experto. Busca y compila información de internet.

Herramientas disponibles:
- web_search: Busca información en internet
- web_fetch: Obtiene contenido detallado de páginas web

Tienes acceso a herramientas de filesystem para guardar resultados.
Usa búsqueda web para encontrar información actualizada y fuentes relevantes."""


# Skills simplificados para Researcher
RESEARCHER_SKILLS = [
    Skill(
        id="research",
        name="Investigación Web",
        description="Búsqueda y compilación de información de fuentes online"
    )
]


class ResearcherAgent(BaseSubAgent):
    """Subagente de investigación usando LLM con herramientas web."""

    id = "researcher_agent"
    name = "Researcher"
    description = "Investigador: búsqueda web, datos actuales, fuentes"
    version = "3.0.0"
    domain_tools = ["web_search", "web_fetch"]
    available_skills = RESEARCHER_SKILLS

    role = "Investigador"
    expertise = "Experto en búsqueda y compilación de información de internet"
    task_requirements = "Describe qué información necesitas investigar"

    def __init__(self):
        super().__init__()
        self.system_prompt = _read_system_prompt()
        logger.info("🔍 ResearcherAgent initialized (shared loop)")

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
        """Ejecuta investigación usando el bucle compartido (run_session_loop)."""
        start_time = time.time()
        logger.info("🔍 ResearcherAgent executing", task=task[:80])
        if not llm_url or not model or not provider_type:
            return SubAgentResult(
                success=False,
                response="❌ **Error:** Se requiere configuración LLM para este agente.\n\nPor favor, configure un modelo LLM en la sección de Configuración.",
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
            logger.error(f"ResearcherAgent error: {e}", exc_info=True)
            return SubAgentResult(
                success=False,
                response=f"❌ **Error en investigación:** {str(e)}",
                agent_id=self.id,
                agent_name=self.name,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )


# Instancia para registro
researcher_agent = ResearcherAgent()
