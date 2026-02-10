"""
SAP Analyst Agent - Análisis de datos y reportes SAP.

Subagente especializado en:
- Conexión a sistemas SAP (S/4HANA, ECC, BI/BW)
- Extracción de datos vía RFC, OData, queries
- Análisis estadístico y generación de insights
- Creación de reportes y dashboards

Sistema de Skills: carga conocimiento especializado según el tipo de análisis.
"""

import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

import structlog

from ..base import BaseSubAgent, SubAgentResult, Skill

logger = structlog.get_logger()


def _read_system_prompt() -> str:
    """Lee el prompt de sistema desde fichero."""
    path = Path(__file__).parent / "prompts" / "system_prompt.txt"
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return """Eres un Analista de Datos SAP BIW (Business Intelligence Warehouse) experto. Tu misión es extraer, analizar y reportar 
datos desde sistemas SAP BW/BI según las necesidades del usuario.

Capacidades:
- Extraer datos desde InfoCubes (cubos OLAP) multidimensionales
- Consultar DSOs (DataStore Objects) para datos maestros y transaccionales
- Ejecutar queries BEx con filtros, variables y selecciones
- Obtener jerarquías, atributos y datos maestros
- Trabajar con Key Figures (ratios) y Characteristics (características)
- Análisis estadístico: tendencias, correlaciones, anomalías
- Generar reportes ejecutivos con insights accionables
- Exportar datos en múltiples formatos

Herramientas BIW disponibles:
- biw_get_cube_data: Extraer datos de InfoCubes con navegación multidimensional
- biw_get_dso_data: Extraer datos de DataStore Objects
- biw_get_bex_query: Ejecutar queries BEx con parámetros
- biw_get_master_data: Obtener datos maestros con atributos
- biw_get_hierarchy: Obtener jerarquías (geográficas, organizativas, de producto)
- biw_get_texts: Obtener textos descriptivos
- biw_get_ratios: Obtener ratios calculados (KPIs)

Proceso de trabajo:
1. Entender qué datos necesita el usuario (InfoCube, DSO, query BEx)
2. Identificar características (ejes de análisis) y ratios (medidas)
3. Aplicar filtros y variables según los requerimientos
4. Ejecutar la extracción usando las herramientas BIW
5. Analizar los datos según la petición (análisis multidimensional, tendencias, comparativas)
6. Generar un reporte claro con hallazgos, insights y recomendaciones

Notas importantes:
- Los InfoCubes son multidimensionales: usa características para filtrar y navegar
- Las jerarquías permiten drill-down (ej: Año → Trimestre → Mes)
- Los ratios pueden ser simples o calculados (formulas complejas)
- Siempre valida la integridad de los datos y reporta anomalías

Siempre valida la integridad de los datos y reporta cualquier anomalía encontrada."""


# Skills disponibles para el SAP BIW Analyst
SAP_ANALYST_SKILLS = [
    Skill(
        id="biw_data_extraction",
        name="Extracción de Datos BIW",
        description="Extracción de datos desde SAP BW/BI: InfoCubes, DSOs, queries BEx, InfoProviders"
    ),
    Skill(
        id="biw_reporting",
        name="Reporting y Analytics BIW",
        description="Creación de reportes BIW: BEx Analyzer, Web Intelligence, dashboards y visualizaciones"
    ),
    Skill(
        id="biw_cube_analysis",
        name="Análisis de InfoCubes",
        description="Análisis multidimensional: navegación por características, ratios clave, agregaciones"
    ),
    Skill(
        id="biw_master_data",
        name="Datos Maestros BIW",
        description="Gestión de atributos, jerarquías, textos y datos maestros en BW"
    ),
    Skill(
        id="sap_query_advanced",
        name="Queries SAP Avanzadas",
        description="Técnicas avanzadas de extracción: joins, variants, selecciones dinámicas, optimización"
    ),
    Skill(
        id="statistical_methods",
        name="Métodos Estadísticos",
        description="Análisis estadístico: regresión, correlación, forecasting, análisis de varianza"
    )
]


class SAPAnalystAgent(BaseSubAgent):
    """
    Subagente especializado en análisis de datos SAP BIW (Business Intelligence Warehouse).
    
    Extrae datos desde SAP BW/BI y los analiza según requerimientos,
    generando reportes con insights y recomendaciones.
    """
    
    id = "sap_analyst"
    name = "SAP BIW Analyst"
    description = "Analista de datos SAP BIW: extracción BW, cubos OLAP, reportes y análisis multidimensional"
    version = "1.0.0"
    domain_tools = [
        "biw_get_cube_data",           # Extraer datos de InfoCubes
        "biw_get_dso_data",            # Extraer datos de DSOs
        "biw_get_bex_query",           # Ejecutar queries BEx
        "biw_get_master_data",         # Obtener datos maestros
        "biw_get_hierarchy",           # Obtener jerarquías
        "biw_get_texts",               # Obtener textos
        "biw_get_ratios",              # Obtener ratios/calculated key figures
        "filesystem",                  # Para leer/escribir archivos
        "execute_code"                 # Para análisis estadístico
    ]
    available_skills = SAP_ANALYST_SKILLS
    
    role = "Analista de Datos SAP BIW Senior"
    expertise = """Experto en extracción y análisis de datos desde SAP BW/BI (Business Intelligence Warehouse).
    
Especializado en:
- InfoCubes (cubos OLAP) y navegación multidimensional
- DSOs (DataStore Objects) para datos maestros y transaccionales
- Queries BEx y reporting estructurado
- Jerarquías, atributos y datos maestros
- Key Figures (ratios) y Characteristics (características)
- Filtros, variables y selecciones dinámicas

Técnicas de análisis:
- Análisis multidimensional (slicing, dicing, drill-down)
- Comparativas y variaciones (YoY, MoM)
- Forecasting y tendencias temporales
- ABC analysis y Pareto
- Correlaciones entre KPIs

Genera reportes ejecutivos, dashboards y visualizaciones a partir de datos BW."""
    
    task_requirements = """Para analizar datos SAP BIW necesito:

**Obligatorio:**
- Qué datos necesitas (InfoCube, DSO, query BEx específico)
- Período de análisis (fechas desde/hasta o período fiscal)
- Características clave (ej: sociedad, centro, producto, cliente)

**Opcional pero recomendado:**
- Qué tipo de análisis requieres (cubo, tendencias, comparativas, drill-down)
- Jerarquías a utilizar (ej: geografía, organización, producto)
- Ratios/KPIs específicos a calcular
- Filtros y variables (ej: solo activos, solo 2024, etc.)
- Formato de salida deseado (Excel, CSV, PDF, JSON, tabla)

**Ejemplos:**
- "Análisis de ventas del último trimestre por región y producto desde el cubo ZC_SALES"
- "Drill-down de costes por centro de coste y mes fiscal desde ZC_COSTS"
- "Comparativa YoY de margen por cliente desde la query BEx ZQ_MARGIN"
- "Datos maestros de materiales con atributos desde el DSO ZDSO_MATERIAL"
"""
    
    def __init__(self):
        super().__init__()
        self._connection_cache: Dict[str, Any] = {}
        logger.info(f"📊 SAPAnalystAgent initialized with {len(self.available_skills)} skills")
    
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
        Ejecuta análisis de datos SAP según la petición.
        
        Args:
            task: Descripción de la tarea de análisis
            context: Contexto adicional (datos de conexión, configuraciones)
            llm_url: URL del LLM para procesamiento
            model: Modelo LLM a usar
            provider_type: Tipo de proveedor LLM
            api_key: API key para LLM
            
        Returns:
            SubAgentResult con el reporte de análisis
        """
        start_time = time.time()
        logger.info("📊 SAPAnalystAgent executing", task=task[:80])
        
        try:
            # Parsear la petición
            task_data = self._parse_task(task)
            
            # Validar requisitos mínimos
            validation = self._validate_requirements(task_data)
            if not validation["valid"]:
                return SubAgentResult(
                    success=False,
                    response=f"❌ **Faltan datos obligatorios:**\n\n{validation['message']}\n\nPor favor, proporciona la información necesaria e intenta de nuevo.",
                    agent_id=self.id,
                    agent_name=self.name,
                    error="Missing required parameters",
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
            
            # Determinar skills relevantes y cargarlos
            relevant_skills = self._determine_relevant_skills(task_data)
            loaded_skills_content = []
            for skill_id in relevant_skills:
                skill_result = self.load_skill(skill_id)
                if skill_result["success"]:
                    loaded_skills_content.append(f"\n### {skill_id}\n{skill_result['content']}")
            
            # Fase 1: Extracción de datos
            extraction_result = await self._extract_data(
                task_data, 
                context,
                loaded_skills_content
            )
            
            if not extraction_result["success"]:
                return SubAgentResult(
                    success=False,
                    response=f"❌ **Error en extracción de datos:**\n\n{extraction_result.get('error', 'Error desconocido')}",
                    agent_id=self.id,
                    agent_name=self.name,
                    error=extraction_result.get("error"),
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
            
            # Fase 2: Análisis de datos
            analysis_result = await self._analyze_data(
                task_data,
                extraction_result["data"],
                loaded_skills_content,
                llm_url,
                model,
                provider_type,
                api_key
            )
            
            # Fase 3: Generar reporte final
            report = self._generate_report(
                task_data,
                extraction_result,
                analysis_result
            )
            
            execution_time = int((time.time() - start_time) * 1000)
            
            return SubAgentResult(
                success=True,
                response=report,
                agent_id=self.id,
                agent_name=self.name,
                tools_used=["execute_code", "filesystem"],
                data={
                    "extraction": extraction_result,
                    "analysis": analysis_result,
                    "skills_used": relevant_skills,
                    "execution_time_ms": execution_time
                },
                execution_time_ms=execution_time
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
    
    def _parse_task(self, task: str) -> Dict[str, Any]:
        """Parsea la tarea en componentes estructurados."""
        try:
            # Intentar parsear como JSON
            data = json.loads(task)
            return {
                "description": data.get("task", data.get("description", task)),
                "module": data.get("module", ""),
                "tables": data.get("tables", []),
                "fields": data.get("fields", []),
                "period": data.get("period", {}),
                "filters": data.get("filters", {}),
                "analysis_type": data.get("analysis_type", "descriptive"),
                "output_format": data.get("output_format", "report"),
                "comparison": data.get("comparison", False),
                "group_by": data.get("group_by", []),
                "metrics": data.get("metrics", []),
                "connection": data.get("connection", {}),
                "raw": task
            }
        except (json.JSONDecodeError, TypeError):
            # Parseo manual desde texto libre
            return {
                "description": task,
                "module": self._extract_module(task),
                "tables": [],
                "fields": [],
                "period": self._extract_period(task),
                "filters": {},
                "analysis_type": self._detect_analysis_type(task),
                "output_format": "report",
                "comparison": self._detect_comparison(task),
                "group_by": [],
                "metrics": [],
                "connection": {},
                "raw": task
            }
    
    def _extract_module(self, text: str) -> str:
        """Extrae el módulo SAP mencionado."""
        text_lower = text.lower()
        modules = {
            "fi": ["financiero", "contable", "balance", "cuenta", "fi/"],
            "co": ["controlling", "coste", "centro de coste", "profit center", "co/"],
            "sd": ["ventas", "cliente", "pedido", "factura", "sd/", "billing"],
            "mm": ["material", "inventario", "stock", "compra", "proveedor", "mm/"],
            "pp": ["producción", "orden", "fabricación", "pp/", "bom"],
            "hr": ["personal", "empleado", "nómina", "hr/", "hcm", "recursos humanos"]
        }
        for mod, keywords in modules.items():
            if any(kw in text_lower for kw in keywords):
                return mod.upper()
        return ""
    
    def _extract_period(self, text: str) -> Dict[str, str]:
        """Extrae el período de análisis."""
        import re
        period = {}
        
        # Buscar fechas
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',
            r'((?:ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)[a-z]*)',
            r'(trimestre|quarter|q)[ ]?([1-4])',
            r'(año|year)[ ]?(20)?(19)?(20)?(21)?(22)?(23)?(24)?(25)?(26)?(27)?(28)?(29)?',
        ]
        
        # Patrones de período comunes
        if "último mes" in text.lower() or "last month" in text.lower():
            period["type"] = "last_month"
        elif "último trimestre" in text.lower() or "last quarter" in text.lower():
            period["type"] = "last_quarter"
        elif "último año" in text.lower() or "last year" in text.lower():
            period["type"] = "last_year"
        elif "año anterior" in text.lower() or "previous year" in text.lower():
            period["type"] = "previous_year"
        elif "ytd" in text.lower() or "year to date" in text.lower():
            period["type"] = "ytd"
        else:
            period["type"] = "custom"
        
        return period
    
    def _detect_analysis_type(self, text: str) -> str:
        """Detecta el tipo de análisis requerido."""
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["tendencia", "trend", "forecast", "predicción", "projection"]):
            return "forecasting"
        elif any(kw in text_lower for kw in ["comparar", "comparativa", "vs", "versus", "comparación", "comparison"]):
            return "comparative"
        elif any(kw in text_lower for kw in ["correlación", "correlation", "regresión", "regression"]):
            return "correlation"
        elif any(kw in text_lower for kw in ["anomalía", "anomaly", "outlier", "detección", "detection"]):
            return "anomaly_detection"
        elif any(kw in text_lower for kw in ["abc", "pareto", "clasificación", "classification"]):
            return "abc_analysis"
        else:
            return "descriptive"
    
    def _detect_comparison(self, text: str) -> bool:
        """Detecta si se requiere comparación."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in ["comparar", "comparativa", "vs", "versus", "año anterior", "previous year", "contraste"])
    
    def _validate_requirements(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida que se proporcionen los requisitos mínimos."""
        missing = []
        
        if not task_data.get("description"):
            missing.append("Descripción de los datos a analizar")
        
        if not task_data.get("module") and not task_data.get("tables"):
            missing.append("Módulo SAP o tablas de origen (ej: FI, SD, VBAK, BSEG)")
        
        if not task_data.get("period"):
            missing.append("Período de análisis (fechas o período relativo)")
        
        if missing:
            return {
                "valid": False,
                "message": "\n".join([f"• {m}" for m in missing])
            }
        
        return {"valid": True, "message": ""}
    
    def _determine_relevant_skills(self, task_data: Dict[str, Any]) -> List[str]:
        """Determina qué skills son relevantes para la tarea."""
        skills = []
        module = task_data.get("module", "").lower()
        analysis_type = task_data.get("analysis_type", "")
        
        # Skills por módulo
        if module in ["fi", "co"]:
            skills.append("financial_analysis")
        elif module == "sd":
            skills.append("sales_analysis")
        elif module == "mm":
            skills.append("inventory_analysis")
        elif module == "pp":
            skills.append("production_analysis")
        elif module == "hr":
            skills.append("hr_analysis")
        
        # Skills por tipo de análisis
        if analysis_type in ["forecasting", "correlation", "anomaly_detection", "abc_analysis"]:
            skills.append("statistical_methods")
        
        # Skill de queries avanzadas siempre útil
        skills.append("sap_query_advanced")
        
        return skills
    
    async def _extract_data(
        self,
        task_data: Dict[str, Any],
        context: Optional[str],
        skills_content: List[str]
    ) -> Dict[str, Any]:
        """Extrae datos desde SAP según la configuración."""
        
        # Generar código de extracción basado en el contexto y skills
        extraction_code = self._generate_extraction_code(task_data, context, skills_content)
        
        logger.info("🔄 Extracting SAP data", 
                   module=task_data.get("module"), 
                   analysis_type=task_data.get("analysis_type"))
        
        # Ejecutar código de extracción
        try:
            from src.tools.core.execution import execute_code
            
            exec_result = await execute_code(
                language="python",
                code=extraction_code,
                timeout=120
            )
            
            if exec_result.get("success"):
                # Parsear resultado
                output = exec_result.get("output", "")
                try:
                    # Intentar extraer JSON del output
                    json_start = output.find('{"data":')
                    if json_start == -1:
                        json_start = output.find('{"status":')
                    
                    if json_start != -1:
                        json_str = output[json_start:]
                        result_data = json.loads(json_str)
                        return {
                            "success": True,
                            "data": result_data.get("data", {}),
                            "metadata": result_data.get("metadata", {}),
                            "rows": result_data.get("metadata", {}).get("rows", 0),
                            "source": task_data.get("module", "SAP")
                        }
                except:
                    pass
                
                return {
                    "success": True,
                    "data": {"raw_output": output},
                    "metadata": {},
                    "rows": 0,
                    "source": task_data.get("module", "SAP")
                }
            else:
                return {
                    "success": False,
                    "error": exec_result.get("error", "Extracción fallida"),
                    "output": exec_result.get("output", "")
                }
                
        except Exception as e:
            logger.error(f"Data extraction error: {e}")
            return {
                "success": False,
                "error": f"Error en extracción: {str(e)}"
            }
    
    def _generate_extraction_code(
        self,
        task_data: Dict[str, Any],
        context: Optional[str],
        skills_content: List[str]
    ) -> str:
        """Genera código Python para extraer datos de SAP."""
        
        module = task_data.get("module", "GENERIC")
        tables = task_data.get("tables", [])
        fields = task_data.get("fields", [])
        period = task_data.get("period", {})
        filters = task_data.get("filters", {})
        
        # Código base que simula extracción SAP
        code = f'''#!/usr/bin/env python3
"""
Extracción de datos SAP - {module}
Generado automáticamente por SAPAnalystAgent
"""

import json
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

# Simulación de conexión SAP (en producción usar pyrfc, pyodata, etc.)
def extract_sap_data():
    """Extrae datos desde SAP."""
    
    # Configuración de extracción
    module = "{module}"
    tables = {tables if tables else ["VBAK", "VBAP", "KNA1" if module == "SD" else "BSEG", "BKPF" if module in ["FI", "CO"] else "MARA", "MARD"]}
    fields = {fields if fields else []}
    
    # Período
    period_config = {dict(period)}
    
    # Generar datos simulados para demostración
    # En producción, aquí iría la llamada real a SAP
    print(f"🔗 Conectando a SAP ({module})...")
    print(f"📊 Extrayendo de tablas: {{', '.join(tables)}}")
    
    # Simulación de datos extraídos
    np.random.seed(42)
    n_rows = 1000
    
    data = {{}}
    
    if module == "SD":
        # Datos de ventas
        data["sales"] = {{
            "document_number": [f"900000{{i:05d}}" for i in range(n_rows)],
            "customer": np.random.choice(["C001", "C002", "C003", "C004", "C005"], n_rows),
            "material": np.random.choice(["M001", "M002", "M003", "M004"], n_rows),
            "quantity": np.random.randint(1, 100, n_rows),
            "amount": np.round(np.random.uniform(100, 10000, n_rows), 2),
            "order_date": pd.date_range(end=datetime.now(), periods=n_rows, freq='H').tolist(),
            "region": np.random.choice(["Norte", "Sur", "Este", "Oeste"], n_rows)
        }}
    elif module in ["FI", "CO"]:
        # Datos financieros
        data["financial"] = {{
            "document": [f"100000{{i:05d}}" for i in range(n_rows)],
            "account": np.random.choice(["1000", "2000", "3000", "4000"], n_rows),
            "amount": np.round(np.random.uniform(-5000, 5000, n_rows), 2),
            "posting_date": pd.date_range(end=datetime.now(), periods=n_rows, freq='H').tolist(),
            "company_code": np.random.choice(["1000", "2000"], n_rows),
            "cost_center": np.random.choice(["CC01", "CC02", "CC03"], n_rows)
        }}
    elif module == "MM":
        # Datos de inventario
        data["inventory"] = {{
            "material": [f"MAT{{i:05d}}" for i in range(500)],
            "plant": np.random.choice(["1000", "2000", "3000"], 500),
            "stock_quantity": np.random.randint(0, 10000, 500),
            "stock_value": np.round(np.random.uniform(0, 100000, 500), 2),
            "movement_type": np.random.choice(["101", "102", "201", "202", "261", "262"], 500),
            "last_movement": pd.date_range(end=datetime.now(), periods=500, freq='2H').tolist()
        }}
    else:
        # Datos genéricos
        data["generic"] = {{
            "id": range(n_rows),
            "value": np.random.uniform(0, 100, n_rows),
            "category": np.random.choice(["A", "B", "C"], n_rows),
            "timestamp": pd.date_range(end=datetime.now(), periods=n_rows, freq='H').tolist()
        }}
    
    # Metadata
    metadata = {{
        "module": module,
        "tables": tables,
        "extracted_at": datetime.now().isoformat(),
        "rows": n_rows,
        "period": period_config,
        "filters_applied": {dict(filters)}
    }}
    
    # Output final
    result = {{
        "status": "success",
        "data": data,
        "metadata": metadata
    }}
    
    print(json.dumps(result))
    return result

if __name__ == "__main__":
    extract_sap_data()
'''
        
        return code
    
    async def _analyze_data(
        self,
        task_data: Dict[str, Any],
        data: Dict[str, Any],
        skills_content: List[str],
        llm_url: Optional[str],
        model: Optional[str],
        provider_type: str,
        api_key: Optional[str]
    ) -> Dict[str, Any]:
        """Analiza los datos extraídos según los requerimientos."""
        
        analysis_type = task_data.get("analysis_type", "descriptive")
        
        logger.info("📈 Analyzing data", analysis_type=analysis_type)
        
        # Generar código de análisis
        analysis_code = self._generate_analysis_code(task_data, skills_content)
        
        try:
            from src.tools.core.execution import execute_code
            
            exec_result = await execute_code(
                language="python",
                code=analysis_code,
                timeout=180
            )
            
            if exec_result.get("success"):
                output = exec_result.get("output", "")
                
                # Intentar extraer resultados
                try:
                    json_start = output.find('{"analysis":')
                    if json_start != -1:
                        json_str = output[json_start:]
                        result_data = json.loads(json_str)
                        return {
                            "success": True,
                            "insights": result_data.get("analysis", {}),
                            "statistics": result_data.get("statistics", {}),
                            "recommendations": result_data.get("recommendations", [])
                        }
                except:
                    pass
                
                return {
                    "success": True,
                    "insights": {{"raw_analysis": output}},
                    "statistics": {{}},
                    "recommendations": []
                }
            else:
                return {
                    "success": False,
                    "error": exec_result.get("error", "Análisis fallido"),
                    "insights": {{}},
                    "recommendations": []
                }
                
        except Exception as e:
            logger.error(f"Data analysis error: {e}")
            return {
                "success": False,
                "error": str(e),
                "insights": {{}},
                "recommendations": []
            }
    
    def _generate_analysis_code(
        self,
        task_data: Dict[str, Any],
        skills_content: List[str]
    ) -> str:
        """Genera código Python para análisis de datos."""
        
        analysis_type = task_data.get("analysis_type", "descriptive")
        module = task_data.get("module", "GENERIC")
        comparison = task_data.get("comparison", False)
        
        code = f'''#!/usr/bin/env python3
"""
Análisis de datos SAP - {analysis_type}
Generado automáticamente por SAPAnalystAgent
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Cargar datos (en producción vendrían del paso anterior)
# Aquí recreamos datos de ejemplo para el análisis

np.random.seed(42)
n_rows = 1000

# Recrear datos según el módulo
if "{module}" == "SD":
    df = pd.DataFrame({{
        "document_number": [f"900000{{i:05d}}" for i in range(n_rows)],
        "customer": np.random.choice(["C001", "C002", "C003", "C004", "C005"], n_rows),
        "material": np.random.choice(["M001", "M002", "M003", "M004"], n_rows),
        "quantity": np.random.randint(1, 100, n_rows),
        "amount": np.round(np.random.uniform(100, 10000, n_rows), 2),
        "order_date": pd.date_range(end=datetime.now(), periods=n_rows, freq='H'),
        "region": np.random.choice(["Norte", "Sur", "Este", "Oeste"], n_rows)
    }})
elif "{module}" in ["FI", "CO"]:
    df = pd.DataFrame({{
        "document": [f"100000{{i:05d}}" for i in range(n_rows)],
        "account": np.random.choice(["1000", "2000", "3000", "4000"], n_rows),
        "amount": np.round(np.random.uniform(-5000, 5000, n_rows), 2),
        "posting_date": pd.date_range(end=datetime.now(), periods=n_rows, freq='H'),
        "company_code": np.random.choice(["1000", "2000"], n_rows),
        "cost_center": np.random.choice(["CC01", "CC02", "CC03"], n_rows)
    }})
elif "{module}" == "MM":
    df = pd.DataFrame({{
        "material": [f"MAT{{i:05d}}" for i in range(500)],
        "plant": np.random.choice(["1000", "2000", "3000"], 500),
        "stock_quantity": np.random.randint(0, 10000, 500),
        "stock_value": np.round(np.random.uniform(0, 100000, 500), 2),
        "movement_type": np.random.choice(["101", "102", "201", "202", "261", "262"], 500),
        "last_movement": pd.date_range(end=datetime.now(), periods=500, freq='2H')
    }})
else:
    df = pd.DataFrame({{
        "id": range(n_rows),
        "value": np.random.uniform(0, 100, n_rows),
        "category": np.random.choice(["A", "B", "C"], n_rows),
        "timestamp": pd.date_range(end=datetime.now(), periods=n_rows, freq='H')
    }})

# Análisis según tipo
analysis_results = {{}}
statistics = {{}}
recommendations = []

if "{analysis_type}" == "descriptive":
    # Estadísticas descriptivas
    statistics["summary"] = df.describe().to_dict()
    statistics["total_records"] = len(df)
    
    if "{module}" == "SD":
        analysis_results["total_sales"] = df["amount"].sum()
        analysis_results["avg_order_value"] = df["amount"].mean()
        analysis_results["total_orders"] = len(df)
        analysis_results["top_customers"] = df.groupby("customer")["amount"].sum().sort_values(ascending=False).head(5).to_dict()
        analysis_results["sales_by_region"] = df.groupby("region")["amount"].sum().to_dict()
        analysis_results["top_products"] = df.groupby("material")["amount"].sum().sort_values(ascending=False).head(5).to_dict()
        
        recommendations.append("Los 5 principales clientes generan " + 
            f"{{df.groupby('customer')['amount'].sum().sort_values(ascending=False).head(5).sum() / df['amount'].sum() * 100:.1f}}% del volumen total")
        
    elif "{module}" in ["FI", "CO"]:
        analysis_results["total_debits"] = df[df["amount"] > 0]["amount"].sum()
        analysis_results["total_credits"] = abs(df[df["amount"] < 0]["amount"].sum())
        analysis_results["net_balance"] = df["amount"].sum()
        analysis_results["by_account"] = df.groupby("account")["amount"].sum().to_dict()
        analysis_results["by_cost_center"] = df.groupby("cost_center")["amount"].sum().to_dict()
        
        if analysis_results["net_balance"] > 0:
            recommendations.append(f"Saldo neto positivo de {{analysis_results['net_balance']:,.2f}}. Revisar conciliación.")
        
    elif "{module}" == "MM":
        analysis_results["total_stock_value"] = df["stock_value"].sum()
        analysis_results["avg_stock_quantity"] = df["stock_quantity"].mean()
        analysis_results["high_value_materials"] = df.nlargest(10, "stock_value")[["material", "stock_value"]].to_dict("records")
        analysis_results["zero_stock"] = len(df[df["stock_quantity"] == 0])
        
        if analysis_results["zero_stock"] > 0:
            recommendations.append(f"{{analysis_results['zero_stock']}} materiales sin stock. Revisar planificación.")

elif "{analysis_type}" == "forecasting":
    # Análisis de tendencias simple
    if "order_date" in df.columns or "posting_date" in df.columns:
        date_col = "order_date" if "order_date" in df.columns else "posting_date"
        df["period"] = pd.to_datetime(df[date_col]).dt.to_period('M')
        
        if "amount" in df.columns:
            trend = df.groupby("period")["amount"].sum()
            analysis_results["monthly_trend"] = trend.to_dict()
            analysis_results["trend_direction"] = "creciente" if trend.iloc[-1] > trend.iloc[0] else "decreciente"
            analysis_results["trend_change_pct"] = ((trend.iloc[-1] - trend.iloc[0]) / abs(trend.iloc[0]) * 100) if trend.iloc[0] != 0 else 0
            
            recommendations.append(f"Tendencia {{analysis_results['trend_direction']}} del {{abs(analysis_results['trend_change_pct']):.1f}}% en el período")

elif "{analysis_type}" == "abc_analysis":
    # Análisis ABC/Pareto
    if "amount" in df.columns:
        if "material" in df.columns:
            grouped = df.groupby("material")["amount"].sum().sort_values(ascending=False)
        elif "customer" in df.columns:
            grouped = df.groupby("customer")["amount"].sum().sort_values(ascending=False)
        else:
            grouped = df.groupby(df.index // (len(df) // 10))["amount"].sum().sort_values(ascending=False)
        
        total = grouped.sum()
        cumulative = grouped.cumsum()
        
        # Clasificación ABC
        abc = pd.DataFrame({{
            "value": grouped,
            "percentage": grouped / total * 100,
            "cumulative_pct": cumulative / total * 100
        }})
        
        abc["class"] = pd.cut(abc["cumulative_pct"], 
                             bins=[0, 80, 95, 100], 
                             labels=["A", "B", "C"])
        
        analysis_results["abc_distribution"] = abc.groupby("class").agg({{
            "value": "sum",
            "percentage": "sum"
        }}).to_dict()
        
        analysis_results["class_a_items"] = len(abc[abc["class"] == "A"])
        analysis_results["class_a_contribution"] = abc[abc["class"] == "A"]["percentage"].sum()
        
        recommendations.append(f"Clase A: {{analysis_results['class_a_items']}} items ({{analysis_results['class_a_contribution']:.1f}}% del valor). Priorizar gestión.")

# Preparar resultado
result = {{
    "status": "success",
    "analysis": analysis_results,
    "statistics": statistics,
    "recommendations": recommendations,
    "analyzed_at": datetime.now().isoformat()
}}

print(json.dumps(result, indent=2, default=str))
'''
        
        return code
    
    def _generate_report(
        self,
        task_data: Dict[str, Any],
        extraction_result: Dict[str, Any],
        analysis_result: Dict[str, Any]
    ) -> str:
        """Genera el reporte final de análisis."""
        
        module = task_data.get("module", "SAP")
        analysis_type = task_data.get("analysis_type", "descriptive")
        description = task_data.get("description", "Análisis de datos SAP")
        
        parts = [
            f"# 📊 Reporte de Análisis SAP - {module}",
            f"\n**Tarea:** {description}",
            f"\n**Tipo de análisis:** {analysis_type.title()}",
            f"\n**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"\n---\n"
        ]
        
        # Resumen de extracción
        metadata = extraction_result.get("metadata", {})
        parts.append(f"\n## 📥 Resumen de Extracción\n")
        parts.append(f"- **Registros extraídos:** {metadata.get('rows', 'N/A')}")
        parts.append(f"- **Módulo:** {metadata.get('module', module)}")
        parts.append(f"- **Tablas:** {', '.join(metadata.get('tables', []))}")
        parts.append(f"\n")
        
        # Resultados del análisis
        insights = analysis_result.get("insights", {})
        if insights:
            parts.append(f"\n## 📈 Hallazgos Principales\n")
            
            for key, value in insights.items():
                if isinstance(value, dict):
                    parts.append(f"\n### {key.replace('_', ' ').title()}\n")
                    for k, v in value.items():
                        if isinstance(v, (int, float)):
                            parts.append(f"- **{k}:** {v:,.2f}" if isinstance(v, float) else f"- **{k}:** {v:,}")
                        else:
                            parts.append(f"- **{k}:** {v}")
                elif isinstance(value, list):
                    parts.append(f"\n### {key.replace('_', ' ').title()}\n")
                    for item in value[:5]:  # Limitar a 5 items
                        if isinstance(item, dict):
                            parts.append(f"- {item}")
                        else:
                            parts.append(f"- {item}")
                elif isinstance(value, (int, float)):
                    parts.append(f"\n**{key.replace('_', ' ').title()}:** {value:,.2f}" if isinstance(value, float) else f"\n**{key.replace('_', ' ').title()}:** {value:,}")
                else:
                    parts.append(f"\n**{key.replace('_', ' ').title()}:** {value}")
            
            parts.append(f"\n")
        
        # Estadísticas
        statistics = analysis_result.get("statistics", {})
        if statistics:
            parts.append(f"\n## 📊 Estadísticas\n")
            for key, value in statistics.items():
                parts.append(f"- **{key.replace('_', ' ').title()}:** {value}")
            parts.append(f"\n")
        
        # Recomendaciones
        recommendations = analysis_result.get("recommendations", [])
        if recommendations:
            parts.append(f"\n## 💡 Recomendaciones\n")
            for i, rec in enumerate(recommendations, 1):
                parts.append(f"{i}. {rec}")
            parts.append(f"\n")
        
        # Nota sobre datos simulados
        parts.append(f"\n---\n")
        parts.append(f"*⚠️ Nota: Este análisis utiliza datos simulados para demostración. En producción, se conectará a sistemas SAP reales.*")
        
        return "\n".join(parts)


# Instancia para registro
sap_analyst = SAPAnalystAgent()
