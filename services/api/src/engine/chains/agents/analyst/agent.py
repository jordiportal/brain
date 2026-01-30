"""
AnalystAgent - Analista de investigación y datos.

Responsable de:
- Buscar información y estadísticas relevantes
- Procesar y analizar datos
- Generar especificaciones de gráficos
- Verificar fuentes y citar
"""

import json
from typing import Optional, Dict, Any, List

import structlog

from ..base import BaseSubAgent, SubAgentResult

logger = structlog.get_logger()


class AnalystAgent(BaseSubAgent):
    """
    Agente especializado en investigación y análisis de datos.
    
    Tiene acceso a web_search para buscar información y
    python_execute para procesar datos.
    """
    
    id = "analyst_agent"
    name = "Research Analyst"
    description = "Analista de investigación experto en búsqueda de datos y análisis"
    version = "1.0.0"
    
    role = "Analista de Investigación"
    expertise = """Soy experto en investigación y análisis de datos. Puedo ayudarte con:
- Búsqueda de información actualizada en la web
- Encontrar estadísticas y datos relevantes
- Analizar y procesar datos con Python
- Diseñar visualizaciones y gráficos
- Verificar fuentes y proporcionar citas
- Identificar tendencias y patrones en datos"""
    
    task_requirements = """## MODOS DE USO

### Modo Consulta
Envía: {"mode": "consult", "task": "descripción", "data_needs": "tipo de datos necesarios"}
→ Te diré qué datos puedo buscar y qué análisis propongo

### Modo Ejecución
Envía: {"mode": "execute", "task": "descripción", "search_queries": ["query1", "query2"]}
→ Buscaré información y procesaré los datos

### Modo Review
Envía: {"mode": "review", "task": "descripción", "my_proposal": {...}, "other_proposals": [...]}
→ Evaluaré las propuestas desde perspectiva de datos

### Campos que devuelvo:
- data_sources: Fuentes de datos encontradas
- statistics: Estadísticas relevantes
- charts_spec: Especificaciones de gráficos sugeridos
- insights: Conclusiones del análisis
- citations: Citas y referencias
"""
    
    domain_tools: List[str] = ["web_search", "python_execute"]
    
    async def execute(
        self,
        task: str,
        context: Optional[str] = None,
        llm_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_type: str = "openai",
        api_key: Optional[str] = None,
        **kwargs
    ) -> SubAgentResult:
        """
        Ejecuta el agente analista.
        
        Modos:
        - consult: Propone qué datos buscar y qué análisis hacer
        - execute: Busca información y procesa datos
        - review: Evalúa propuestas de otros agentes
        """
        import time
        start_time = time.time()
        
        try:
            task_data = self._parse_task(task)
            mode = task_data.get("mode", "consult")
            
            if mode == "consult":
                return await self._handle_consult(
                    task_data, llm_url, model, provider_type, api_key, start_time
                )
            elif mode == "execute":
                return await self._handle_execute(
                    task_data, llm_url, model, provider_type, api_key, start_time
                )
            elif mode == "review":
                return await self._handle_review(
                    task_data, llm_url, model, provider_type, api_key, start_time
                )
            else:
                return await self._handle_consult(
                    task_data, llm_url, model, provider_type, api_key, start_time
                )
                
        except Exception as e:
            logger.error(f"AnalystAgent error: {e}", exc_info=True)
            return SubAgentResult(
                success=False,
                response=f"Error en análisis: {str(e)}",
                agent_id=self.id,
                agent_name=self.name,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
    
    def _parse_task(self, task: str) -> Dict[str, Any]:
        """Parsea el task string a diccionario."""
        try:
            return json.loads(task)
        except json.JSONDecodeError:
            return {"task": task, "mode": "consult"}
    
    async def _handle_consult(
        self,
        task_data: Dict[str, Any],
        llm_url: Optional[str],
        model: Optional[str],
        provider_type: str,
        api_key: Optional[str],
        start_time: float
    ) -> SubAgentResult:
        """
        Modo consulta: Propone qué datos buscar y qué análisis realizar.
        """
        from ...llm_utils import call_llm_with_tools
        import time
        
        task_desc = task_data.get("task", "")
        data_needs = task_data.get("data_needs", "")
        team_mode = task_data.get("team_mode", False)
        
        prompt = f"""Eres un Analista de Investigación experto en búsqueda y análisis de datos.

**TAREA:** {task_desc}
{f"**DATOS NECESARIOS:** {data_needs}" if data_needs else ""}

Proporciona tu plan de investigación y análisis:

1. **DATOS A BUSCAR**
¿Qué información específica necesitamos?
- Estadísticas clave
- Fuentes recomendadas
- Queries de búsqueda sugeridas

2. **ANÁLISIS PROPUESTO**
¿Qué procesamiento de datos sería útil?
- Comparaciones
- Tendencias
- Cálculos

3. **VISUALIZACIONES SUGERIDAS**
¿Qué gráficos ayudarían?
- Tipo de gráfico (barras, líneas, pie, etc.)
- Datos a mostrar
- Mensaje que transmite

4. **FUENTES POTENCIALES**
¿Dónde buscar esta información?

{"Responde en formato JSON estructurado para facilitar la integración con el equipo." if team_mode else ""}
"""

        try:
            if not llm_url or not api_key:
                return self._default_consult_response(task_desc, start_time)
            
            response = await call_llm_with_tools(
                messages=[
                    {"role": "system", "content": "Eres un analista de datos experto. Responde de forma estructurada y práctica."},
                    {"role": "user", "content": prompt}
                ],
                tools=[],
                temperature=0.5,
                provider_type=provider_type,
                api_key=api_key,
                llm_url=llm_url,
                model=model
            )
            
            content = response.content or ""
            structured_data = self._extract_structured_data(content, task_desc)
            
            return SubAgentResult(
                success=True,
                response=content,
                agent_id=self.id,
                agent_name=self.name,
                data=structured_data,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
            
        except Exception as e:
            logger.error(f"Consult error: {e}")
            return self._default_consult_response(task_desc, start_time)
    
    async def _handle_execute(
        self,
        task_data: Dict[str, Any],
        llm_url: Optional[str],
        model: Optional[str],
        provider_type: str,
        api_key: Optional[str],
        start_time: float
    ) -> SubAgentResult:
        """
        Modo ejecución: Busca información y procesa datos.
        """
        import time
        
        task_desc = task_data.get("task", task_data.get("original_task", ""))
        search_queries = task_data.get("search_queries", [])
        consensus_brief = task_data.get("consensus_brief", {})
        
        results = {
            "searches": [],
            "data_found": [],
            "analysis": None,
            "charts_spec": []
        }
        
        # Ejecutar búsquedas web
        if search_queries:
            for query in search_queries[:3]:  # Máximo 3 búsquedas
                try:
                    search_result = await self._web_search(query)
                    results["searches"].append({
                        "query": query,
                        "results": search_result[:3] if search_result else []
                    })
                except Exception as e:
                    logger.warning(f"Search failed for '{query}': {e}")
        
        # Si no hay queries explícitas, generar algunas basadas en la tarea
        if not search_queries and task_desc:
            auto_queries = self._generate_search_queries(task_desc)
            for query in auto_queries[:2]:
                try:
                    search_result = await self._web_search(query)
                    results["searches"].append({
                        "query": query,
                        "results": search_result[:3] if search_result else []
                    })
                except Exception as e:
                    logger.warning(f"Auto search failed: {e}")
        
        # Compilar datos encontrados
        for search in results["searches"]:
            for r in search.get("results", []):
                if isinstance(r, dict):
                    results["data_found"].append({
                        "source": r.get("url", ""),
                        "title": r.get("title", ""),
                        "snippet": r.get("snippet", "")
                    })
        
        # Generar resumen
        response = self._compile_research_response(results, task_desc)
        
        return SubAgentResult(
            success=True,
            response=response,
            agent_id=self.id,
            agent_name=self.name,
            sources=[{"url": d["source"], "title": d["title"]} for d in results["data_found"] if d.get("source")],
            data=results,
            execution_time_ms=int((time.time() - start_time) * 1000)
        )
    
    async def _handle_review(
        self,
        task_data: Dict[str, Any],
        llm_url: Optional[str],
        model: Optional[str],
        provider_type: str,
        api_key: Optional[str],
        start_time: float
    ) -> SubAgentResult:
        """
        Modo review: Evalúa propuestas desde perspectiva de datos.
        """
        from ...llm_utils import call_llm_with_tools
        import time
        
        task_desc = task_data.get("task", "")
        my_proposal = task_data.get("my_proposal", {})
        other_proposals = task_data.get("other_proposals", [])
        
        others_text = ""
        for p in other_proposals:
            agent = p.get("agent", "Agente")
            content = p.get("content", {})
            content_str = json.dumps(content, ensure_ascii=False)[:500] if isinstance(content, dict) else str(content)[:500]
            others_text += f"\n**{agent}:**\n{content_str}\n"
        
        prompt = f"""Eres un Analista de Datos revisando propuestas del equipo.

**TAREA:** {task_desc}

**PROPUESTAS DE OTROS:**
{others_text}

**EVALÚA DESDE PERSPECTIVA DE DATOS:**
1. ¿Las propuestas están respaldadas por datos?
2. ¿Falta información que debería incluirse?
3. ¿Hay afirmaciones que necesitan verificación?
4. ¿Qué datos adicionales podrían fortalecer la propuesta?

Responde con tu evaluación y sugerencias.
"""

        try:
            if not llm_url or not api_key:
                return SubAgentResult(
                    success=True,
                    response="Acepto las propuestas. Sugiero incluir datos de respaldo.",
                    agent_id=self.id,
                    agent_name=self.name,
                    data={"status": "accepted", "data_suggestions": []},
                    execution_time_ms=int((time.time() - start_time) * 1000)
                )
            
            response = await call_llm_with_tools(
                messages=[
                    {"role": "system", "content": "Eres un analista de datos riguroso."},
                    {"role": "user", "content": prompt}
                ],
                tools=[],
                temperature=0.3,
                provider_type=provider_type,
                api_key=api_key,
                llm_url=llm_url,
                model=model
            )
            
            return SubAgentResult(
                success=True,
                response=response.content or "",
                agent_id=self.id,
                agent_name=self.name,
                data={"status": "reviewed", "feedback": response.content},
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
            
        except Exception as e:
            logger.error(f"Review error: {e}")
            return SubAgentResult(
                success=True,
                response="Acepto las propuestas con observaciones menores.",
                agent_id=self.id,
                agent_name=self.name,
                data={"status": "accepted"},
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
    
    async def _web_search(self, query: str) -> List[Dict[str, Any]]:
        """Ejecuta una búsqueda web usando la herramienta disponible."""
        try:
            from src.tools.core.execution import web_search
            result = await web_search(query)
            if isinstance(result, list):
                return result
            elif isinstance(result, dict):
                return result.get("results", [])
            return []
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return []
    
    def _generate_search_queries(self, task: str) -> List[str]:
        """Genera queries de búsqueda basadas en la tarea."""
        queries = []
        
        # Palabras clave comunes
        task_lower = task.lower()
        
        if "estadísticas" in task_lower or "datos" in task_lower:
            queries.append(f"{task} estadísticas 2024")
        
        if "tendencias" in task_lower or "futuro" in task_lower:
            queries.append(f"{task} tendencias")
        
        # Query genérica
        queries.append(f"{task[:50]} datos actuales")
        
        return queries[:3]
    
    def _compile_research_response(self, results: Dict, task: str) -> str:
        """Compila los resultados de investigación en una respuesta."""
        response_parts = [f"## Resultados de Investigación\n\n**Tarea:** {task}\n"]
        
        if results["searches"]:
            response_parts.append("\n### Búsquedas Realizadas\n")
            for search in results["searches"]:
                response_parts.append(f"- **Query:** {search['query']}\n")
                for r in search.get("results", [])[:2]:
                    if isinstance(r, dict):
                        response_parts.append(f"  - {r.get('title', 'Sin título')}\n")
        
        if results["data_found"]:
            response_parts.append("\n### Datos Encontrados\n")
            for data in results["data_found"][:5]:
                response_parts.append(f"- {data.get('title', 'Sin título')}\n")
                if data.get("snippet"):
                    response_parts.append(f"  > {data['snippet'][:150]}...\n")
        
        if not results["searches"] and not results["data_found"]:
            response_parts.append("\nNo se encontraron datos específicos. Se requiere búsqueda manual.\n")
        
        return "".join(response_parts)
    
    def _default_consult_response(self, task: str, start_time: float) -> SubAgentResult:
        """Respuesta por defecto cuando no hay LLM disponible."""
        import time
        
        response = f"""**Plan de Investigación**

**Tarea:** {task}

**Datos a Buscar:**
- Estadísticas actuales sobre el tema
- Estudios o informes relevantes
- Tendencias recientes

**Análisis Propuesto:**
- Comparación de datos históricos vs actuales
- Identificación de patrones clave

**Visualizaciones Sugeridas:**
- Gráfico de barras para comparaciones
- Línea temporal para tendencias

**Fuentes Potenciales:**
- Informes oficiales
- Estudios académicos
- Noticias recientes
"""
        
        return SubAgentResult(
            success=True,
            response=response,
            agent_id=self.id,
            agent_name=self.name,
            data={
                "search_queries": [f"{task} estadísticas 2024", f"{task} tendencias"],
                "charts_spec": [{"type": "bar", "purpose": "comparación"}],
                "data_sources": ["informes oficiales", "estudios académicos"]
            },
            execution_time_ms=int((time.time() - start_time) * 1000)
        )
    
    def _extract_structured_data(self, content: str, task: str) -> Dict[str, Any]:
        """Intenta extraer datos estructurados del contenido."""
        data = {
            "search_queries": [f"{task[:30]} estadísticas", f"{task[:30]} datos"],
            "charts_spec": [],
            "data_sources": []
        }
        
        content_lower = content.lower()
        
        # Detectar tipos de gráficos mencionados
        chart_types = {
            "barras": "bar",
            "líneas": "line",
            "pie": "pie",
            "torta": "pie",
            "área": "area"
        }
        
        for name, chart_type in chart_types.items():
            if name in content_lower:
                data["charts_spec"].append({"type": chart_type})
        
        return data
