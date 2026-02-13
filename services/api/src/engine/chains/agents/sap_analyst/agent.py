"""
SAP Analyst Agent - Análisis de datos y reportes SAP.

Subagente especializado en:
- Conexión a sistemas SAP (S/4HANA, ECC, BI/BW)
- Extracción de datos vía RFC, OData, queries
- Análisis estadístico y generación de insights
- Creación de reportes y dashboards

Patrón: LLM-Only con Tools
"""

import json
import time
from pathlib import Path
from typing import Optional, Dict, Any

import structlog

from ..base import BaseSubAgent, SubAgentResult, Skill
from ...llm_utils import call_llm_with_tools

logger = structlog.get_logger()


def _read_system_prompt() -> str:
    """Lee el prompt de sistema desde fichero."""
    path = Path(__file__).parent / "prompts" / "system_prompt.txt"
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return """Eres un Analista de Datos SAP BIW (Business Intelligence Warehouse) experto. Tu misión es ayudar con análisis de datos SAP.

Herramientas BIW disponibles:
- biw_get_cube_data: Extraer datos de InfoCubes
- biw_get_dso_data: Extraer datos de DataStore Objects  
- biw_get_bex_query: Ejecutar queries BEx
- biw_get_master_data: Obtener datos maestros
- biw_get_hierarchy: Obtener jerarquías
- biw_get_texts: Obtener textos descriptivos
- biw_get_ratios: Obtener ratios/KPIs
- generate_spreadsheet: Generar archivos Excel con los datos extraídos

También tienes acceso a herramientas de filesystem y ejecución de código para análisis.

Responde a preguntas y ayuda con análisis usando estas herramientas cuando sea necesario."""


# Skills simplificados para SAP Analyst
SAP_ANALYST_SKILLS = [
    Skill(
        id="biw_extraction",
        name="Extracción BIW",
        description="Uso de herramientas BIW para extraer datos: InfoCubes, DSOs, queries BEx"
    ),
    Skill(
        id="biw_analysis",
        name="Análisis BIW",
        description="Técnicas de análisis: multidimensional, tendencias, ABC, correlaciones"
    )
]


class SAPAnalystAgent(BaseSubAgent):
    """
    Subagente especializado en análisis de datos SAP BIW.
    Usa LLM con herramientas BIW para responder consultas.
    """
    
    id = "sap_analyst"
    name = "SAP BIW Analyst"
    description = "Analista de datos SAP BIW: extracción BW, cubos OLAP, reportes"
    version = "2.0.0"
    domain_tools = [
        "biw_get_cube_data",
        "biw_get_dso_data",
        "biw_get_bex_query",
        "biw_get_master_data",
        "biw_get_hierarchy",
        "biw_get_texts",
        "biw_get_ratios",
        "generate_spreadsheet",
        "filesystem",
        "execute_code"
    ]
    available_skills = SAP_ANALYST_SKILLS
    
    role = "Analista de Datos SAP BIW"
    expertise = "Experto en extracción y análisis de datos SAP BW/BI usando herramientas BIW"
    task_requirements = "Consultas sobre datos SAP BIW: InfoCubes, DSOs, queries, análisis"
    
    def __init__(self):
        super().__init__()
        self.system_prompt = _read_system_prompt()
        logger.info(f"📊 SAPAnalystAgent initialized")
    
    async def execute(
        self,
        task: str,
        context: Optional[str] = None,
        llm_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_type: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> SubAgentResult:
        """Ejecuta consulta SAP usando LLM con herramientas."""
        start_time = time.time()
        logger.info("📊 SAPAnalystAgent executing", task=task[:80])
        
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
            logger.error(f"SAPAnalystAgent error: {e}", exc_info=True)
            return SubAgentResult(
                success=False,
                response=f"❌ **Error en análisis SAP:** {str(e)}",
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
        tool_results = []
        data_results = []
        
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
                    logger.info(f"🛠️ Executing BIW tool: {tool_name}", params=tool_params)
                    result = await tool.handler(**tool_params)
                    tool_results.append({"tool": tool_name, "result": result})
                    
                    # Extraer datos del resultado
                    if isinstance(result, dict) and result.get("success"):
                        if result.get("data"):
                            data_results.append({
                                "tool": tool_name,
                                "data": result.get("data")
                            })
                    
                    logger.info(f"✅ BIW tool {tool_name} executed successfully")
                else:
                    logger.warning(f"⚠️ BIW tool {tool_name} not found or no handler")
            except Exception as e:
                logger.error(f"❌ Error executing BIW tool {tool_name}: {e}")
                tool_results.append({"tool": tool_name, "error": str(e)})
        
        return SubAgentResult(
            success=True,
            response=response.content or f"Análisis BIW completado. Herramientas usadas: {', '.join(tools_used)}",
            agent_id=self.id,
            agent_name=self.name,
            tools_used=tools_used,
            data={"tool_results": tool_results, "data_results": data_results} if tool_results else {},
            execution_time_ms=int((time.time() - start_time) * 1000)
        )


# Instancia para registro
sap_analyst = SAPAnalystAgent()
