"""
SAP Analyst Agent - Análisis de datos y reportes SAP BIW.

Subagente especializado en:
- Conexión a SAP BIW via proxy-biw (HTTP directo)
- Extracción de datos: catálogos, queries, dimensiones, ejecución
- Análisis estadístico y generación de insights
- Creación de reportes y dashboards

Patrón: LLM con Tools en loop multi-turno.
El agente ejecuta tools BIW, reenvía los resultados al LLM,
y este decide si necesita más datos o puede generar el resultado final.
"""

import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

import structlog

from ..base import BaseSubAgent, SubAgentResult, Skill
from ...llm_utils import call_llm_with_tools

logger = structlog.get_logger()

MAX_TOOL_ITERATIONS = 8


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
    
    Conecta directamente al proxy-biw via HTTP, leyendo la config
    de conexión (URL + token) de la tabla openapi_connections (slug=sap-biw).
    
    Loop multi-turno:
    1. El LLM decide qué tools llamar (ej: bi_execute_query)
    2. Se ejecutan las tools y los resultados se reenvían al LLM
    3. El LLM decide el siguiente paso (más tools o respuesta final)
    4. Repite hasta respuesta final o límite de iteraciones
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
        logger.info("📊 SAPAnalystAgent initialized (v3.0.0 HTTP direct via proxy-biw)")
    
    async def execute(
        self,
        task: str,
        context: Optional[str] = None,
        llm_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_type: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> SubAgentResult:
        """Ejecuta consulta SAP usando LLM con herramientas en loop multi-turno."""
        start_time = time.time()
        logger.info("📊 SAPAnalystAgent executing", task=task[:80])
        
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
        """
        Ejecuta con LLM en loop multi-turno.
        
        1. El LLM pide tools BIW → se ejecutan → resultados se reenvían al LLM
        2. El LLM usa los datos REALES para decidir siguiente paso
        3. Loop termina cuando el LLM responde sin tool_calls o MAX_TOOL_ITERATIONS
        """
        
        tools = self.get_tools()
        tool_schemas = [tool.to_function_schema() for tool in tools]
        
        tool_index = {}
        for tool in tools:
            tool_index[tool.id] = tool
            if tool.name and tool.name != tool.id:
                tool_index[tool.name] = tool
        
        system_content = self.system_prompt + self.get_skills_for_prompt()
        user_content = f"Tarea: {task}"
        if context:
            user_content += f"\n\nContexto adicional: {context}"
        
        messages: List[Dict] = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]
        
        all_tools_used: List[str] = []
        all_tool_results: List[Dict] = []
        all_data_results: List[Dict] = []
        final_content = ""
        
        for iteration in range(MAX_TOOL_ITERATIONS):
            logger.info(f"📊 SAP Agent iteration {iteration + 1}/{MAX_TOOL_ITERATIONS}")
            
            response = await call_llm_with_tools(
                messages=messages,
                tools=tool_schemas,
                temperature=0.3,
                provider_type=provider_type,
                api_key=api_key,
                llm_url=llm_url,
                model=model
            )
            
            if not response.tool_calls:
                final_content = response.content or ""
                logger.info("📊 SAP Agent: LLM responded without tool calls, finishing")
                break
            
            if response.content:
                final_content = response.content
            
            assistant_msg: Dict[str, Any] = {"role": "assistant", "content": response.content or ""}
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.get("name", ""),
                        "arguments": tc.function.get("arguments", "{}") if isinstance(tc.function.get("arguments"), str) else json.dumps(tc.function.get("arguments", {}))
                    }
                }
                for tc in response.tool_calls
            ]
            messages.append(assistant_msg)
            
            for tc in response.tool_calls:
                tool_name = tc.function.get("name", "")
                tool_params_raw = tc.function.get("arguments", {})
                
                if isinstance(tool_params_raw, str):
                    try:
                        tool_params = json.loads(tool_params_raw)
                    except json.JSONDecodeError:
                        tool_params = {}
                else:
                    tool_params = tool_params_raw or {}
                
                all_tools_used.append(tool_name)
                
                result_str = ""
                try:
                    tool = tool_index.get(tool_name)
                    if tool and tool.handler:
                        logger.info(f"🛠️ Executing tool: {tool_name}", params=tool_params)
                        result = await tool.handler(**tool_params)
                        all_tool_results.append({"tool": tool_name, "result": result})
                        
                        if isinstance(result, dict) and result.get("success") and result.get("data"):
                            all_data_results.append({
                                "tool": tool_name,
                                "data": result["data"]
                            })
                        
                        result_str = json.dumps(result, ensure_ascii=False, default=str)
                        logger.info(f"✅ Tool {tool_name} executed successfully")
                    else:
                        result_str = json.dumps({"error": f"Tool '{tool_name}' not found"})
                        logger.warning(f"⚠️ Tool {tool_name} not found")
                except Exception as e:
                    result_str = json.dumps({"error": str(e)})
                    logger.error(f"❌ Error executing tool {tool_name}: {e}")
                    all_tool_results.append({"tool": tool_name, "error": str(e)})
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_str
                })
        else:
            logger.warning(f"📊 SAP Agent: reached max iterations ({MAX_TOOL_ITERATIONS})")
            if not final_content:
                final_content = f"Análisis BIW completado tras {MAX_TOOL_ITERATIONS} iteraciones. Herramientas usadas: {', '.join(all_tools_used)}"
        
        return SubAgentResult(
            success=True,
            response=final_content or f"Análisis BIW completado. Herramientas usadas: {', '.join(all_tools_used)}",
            agent_id=self.id,
            agent_name=self.name,
            tools_used=all_tools_used,
            data={"tool_results": all_tool_results, "data_results": all_data_results} if all_tool_results else {},
            execution_time_ms=int((time.time() - start_time) * 1000)
        )


sap_analyst = SAPAnalystAgent()
