"""
Researcher Agent - Búsqueda e investigación en internet.

Patrón: LLM-Only con Tools
Realiza investigación web usando LLM con herramientas de búsqueda.
"""

import time
from pathlib import Path
from typing import Optional

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
        logger.info(f"🔍 ResearcherAgent initialized")

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
        """Ejecuta investigación usando LLM con herramientas."""
        start_time = time.time()
        logger.info("🔍 ResearcherAgent executing", task=task[:80])

        # Validar LLM configurado
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
            return await self._execute_with_llm(
                task, context, llm_url, model, provider_type, api_key, start_time
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
        user_content = f"Tarea de investigación: {task}"
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
            temperature=0.3,
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
        sources = []
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
                    
                    # Extraer fuentes del resultado de búsqueda
                    if isinstance(result, dict):
                        if result.get("sources"):
                            sources.extend(result.get("sources", []))
                        if result.get("results") and tool_name == "web_search":
                            # Convertir resultados de búsqueda a fuentes
                            for item in result.get("results", []):
                                if isinstance(item, dict):
                                    sources.append({
                                        "title": item.get("title", ""),
                                        "url": item.get("url", ""),
                                        "snippet": item.get("snippet", "")
                                    })
                    
                    logger.info(f"✅ Tool {tool_name} executed successfully")
                else:
                    logger.warning(f"⚠️ Tool {tool_name} not found or no handler")
            except Exception as e:
                logger.error(f"❌ Error executing tool {tool_name}: {e}")
                tool_results.append({"tool": tool_name, "error": str(e)})
        
        return SubAgentResult(
            success=True,
            response=response.content or f"Investigación completada usando: {', '.join(tools_used)}",
            agent_id=self.id,
            agent_name=self.name,
            tools_used=tools_used,
            sources=sources,
            data={"tool_results": tool_results, "source_count": len(sources)} if tool_results else {},
            execution_time_ms=int((time.time() - start_time) * 1000)
        )


# Instancia para registro
researcher_agent = ResearcherAgent()
