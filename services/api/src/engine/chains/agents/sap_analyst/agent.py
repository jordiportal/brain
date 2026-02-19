"""
SAP Analyst Agent - Análisis de datos y reportes SAP BIW.

Subagente especializado en:
- Conexión a SAP BIW via proxy-biw (HTTP directo)
- Extracción de datos: catálogos, queries, dimensiones, ejecución
- Análisis estadístico y generación de insights
- Creación de reportes y dashboards

Usa el mismo bucle iterativo que el agente principal (run_session_loop);
solo define system_prompt y tools del dominio.
"""

import time
from pathlib import Path
from typing import Optional

import structlog

from ..base import BaseSubAgent, SubAgentResult, Skill

logger = structlog.get_logger()


def _read_system_prompt() -> str:
    """Lee el prompt de sistema desde fichero."""
    path = Path(__file__).parent / "prompts" / "system_prompt.txt"
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return (
            "Eres un Analista de Datos SAP BIW experto. "
            "Usa las herramientas bi_* para extraer datos de SAP BIW y generate_spreadsheet para crear Excel. "
            "NUNCA inventes datos: usa siempre los datos reales obtenidos de las herramientas."
        )


SAP_ANALYST_SKILLS = [
    Skill(
        id="sap_biw_analyst",
        name="SAP BIW Analyst",
        description="Conocimiento de dominio completo: queries KH Lloreda, dimensiones, medidas, versiones, ejemplos de uso. CARGAR SIEMPRE."
    ),
    Skill(
        id="biw_data_extraction",
        name="Extracción BIW",
        description="Técnicas de extracción: InfoCubes, DSOs, queries BEx, navegación multidimensional"
    ),
    Skill(
        id="financial_analysis",
        name="Análisis Financiero",
        description="P&L, márgenes, ratios financieros, comparativas"
    ),
    Skill(
        id="sales_analysis",
        name="Análisis de Ventas",
        description="Ventas por segmento, canal, marca, evolución temporal"
    ),
]


class SAPAnalystAgent(BaseSubAgent):
    """
    Subagente especializado en análisis de datos SAP BIW.
    
    Conecta directamente al proxy-biw via HTTP. Usa el mismo bucle iterativo
    que el agente principal (run_session_loop); solo define system_prompt y tools.
    """

    id = "sap_analyst"
    name = "SAP BIW Analyst"
    description = "Analista de datos SAP BIW: extracción, queries, P&L, reportes via proxy-biw"
    version = "3.0.0"
    domain_tools = [
        "bi_list_catalogs",
        "bi_list_queries",
        "bi_get_metadata",
        "bi_get_dimension_values",
        "bi_execute_query",
        "bw_execute_mdx",
        "generate_spreadsheet",
        "filesystem",
        "execute_code"
    ]
    available_skills = SAP_ANALYST_SKILLS

    role = "Analista de Datos SAP BIW"
    expertise = "Experto en extracción y análisis de datos SAP BIW usando herramientas bi_* conectadas a proxy-biw"
    task_requirements = "Consultas sobre datos SAP BIW: queries, P&L, ventas, análisis"

    def __init__(self):
        super().__init__()
        self.system_prompt = _read_system_prompt()
        logger.info("📊 SAPAnalystAgent initialized (shared loop)")

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
        """Ejecuta consulta SAP usando el bucle compartido (run_session_loop)."""
        start_time = time.time()
        logger.info("📊 SAPAnalystAgent executing", task=task[:80], session_id=session_id)
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
            logger.error(f"SAPAnalystAgent error: {e}", exc_info=True)
            return SubAgentResult(
                success=False,
                response=f"❌ **Error en análisis SAP:** {str(e)}",
                agent_id=self.id,
                agent_name=self.name,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )


sap_analyst = SAPAnalystAgent()
