"""
Researcher Agent - Búsqueda e investigación en internet.

Versión simplificada: execute(task) -> busca -> compila resultados.
Sin modos (consult/execute/review); el prompt guía el uso.
Sistema de Skills: carga conocimiento especializado según la tarea.
"""

import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

import structlog

from ..base import BaseSubAgent, SubAgentResult, Skill

logger = structlog.get_logger()


def _read_system_prompt() -> str:
    """Lee el prompt desde fichero."""
    path = Path(__file__).parent / "prompts" / "system_prompt.txt"
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return "Eres un investigador. Busca información en internet y compila resultados."


# Skills disponibles para el Researcher (el LLM decide cuándo cargar)
RESEARCHER_SKILLS = [
    Skill(
        id="deep_research",
        name="Investigación Profunda",
        description="Estrategias de búsqueda, validación de fuentes, compilación de información"
    )
]


class ResearcherAgent(BaseSubAgent):
    """Subagente de investigación con web_search y sistema de skills."""

    id = "researcher_agent"
    name = "Researcher"
    description = "Investigador: búsqueda web, datos actuales, fuentes"
    version = "2.0.0"  # Versión con skills
    domain_tools = ["web_search"]
    available_skills = RESEARCHER_SKILLS

    role = "Investigador"
    expertise = """Busco información actualizada en internet. Encuentro datos, estadísticas y fuentes relevantes.
Tengo skills especializados en: investigación profunda, validación de fuentes."""

    task_requirements = "Describe qué información necesitas. Puede ser tema, preguntas concretas o contexto."

    def __init__(self):
        super().__init__()
        logger.info(f"🔍 ResearcherAgent initialized with {len(self.available_skills)} skills")

    async def execute(
        self,
        task: str,
        context: Optional[str] = None,
        llm_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_type: str = "ollama",
        api_key: Optional[str] = None
    ) -> SubAgentResult:
        """Busca información y compila resultados."""
        start_time = time.time()
        logger.info("🔍 ResearcherAgent executing", task=task[:80])

        try:
            task_desc = self._parse_task(task)
            queries = self._get_queries(task, task_desc)

            results = {"searches": [], "data_found": []}
            for query in queries[:3]:
                try:
                    search_result = await self._web_search(query)
                    results["searches"].append({
                        "query": query,
                        "results": search_result[:5] if search_result else []
                    })
                    for r in (search_result or [])[:3]:
                        if isinstance(r, dict):
                            results["data_found"].append({
                                "source": r.get("url", ""),
                                "title": r.get("title", ""),
                                "snippet": r.get("snippet", "")
                            })
                except Exception as e:
                    logger.warning(f"Search failed: {e}")

            response = self._compile_response(results, task_desc)
            sources = [{"url": d["source"], "title": d["title"]} for d in results["data_found"] if d.get("source")]

            return SubAgentResult(
                success=True,
                response=response,
                agent_id=self.id,
                agent_name=self.name,
                tools_used=["web_search"],
                sources=sources,
                data=results,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

        except Exception as e:
            logger.error(f"ResearcherAgent error: {e}", exc_info=True)
            return SubAgentResult(
                success=False,
                response=f"Error: {str(e)}",
                agent_id=self.id,
                agent_name=self.name,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

    def _parse_task(self, task: str) -> str:
        """Extrae descripción de la tarea."""
        try:
            data = json.loads(task)
            return data.get("task", data.get("original_task", task))
        except (json.JSONDecodeError, TypeError):
            return task

    def _get_queries(self, task: str, task_desc: str) -> List[str]:
        """Obtiene queries de búsqueda."""
        try:
            data = json.loads(task)
            queries = data.get("search_queries", [])
            if isinstance(queries, list) and queries:
                return [str(q) for q in queries]
        except (json.JSONDecodeError, TypeError):
            pass
        return self._generate_queries(task_desc)

    def _generate_queries(self, task: str) -> List[str]:
        """Genera queries desde la descripción."""
        t = task.lower()
        queries = []
        if any(k in t for k in ["estadística", "dato", "número", "cifra"]):
            queries.append(f"{task[:80]} estadísticas 2024 2025")
        if any(k in t for k in ["tendencia", "futuro", "predicción"]):
            queries.append(f"{task[:80]} tendencias")
        queries.append(f"{task[:80]} datos actuales")
        return queries[:3]

    def _compile_response(self, results: Dict, task: str) -> str:
        """Compila respuesta estructurada."""
        parts = [f"## Resultados de investigación\n\n**Tema:** {task}\n"]

        if results["searches"]:
            parts.append("\n### Búsquedas realizadas\n")
            for s in results["searches"]:
                parts.append(f"- **Query:** {s['query']}\n")
                for r in s.get("results", [])[:2]:
                    if isinstance(r, dict):
                        parts.append(f"  - [{r.get('title', 'Sin título')}]({r.get('url', '')})\n")

        if results["data_found"]:
            parts.append("\n### Datos encontrados\n")
            for d in results["data_found"][:5]:
                if d.get("snippet"):
                    parts.append(f"- **{d.get('title', 'Fuente')}:** {d['snippet']}\n")

        return "".join(parts)

    async def _web_search(self, query: str) -> List[Dict[str, Any]]:
        """Ejecuta búsqueda web."""
        try:
            from src.tools.core.web import web_search
            result = await web_search(query)
            if isinstance(result, list):
                return result
            if isinstance(result, dict):
                return result.get("results", [])
        except Exception as e:
            logger.error(f"Web search error: {e}")
        return []
