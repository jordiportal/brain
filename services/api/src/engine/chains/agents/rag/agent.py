"""
RAG Agent - Subagente de Recuperación Aumentada

Patrón: LLM-Only con Tools
Responde preguntas basándose en documentos indexados en el knowledge base RAG.
"""

import time
from pathlib import Path
from typing import Optional, List

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
        return """Eres un experto en Recuperación de Información y Generación Aumentada (RAG).
Tu propósito es responder preguntas precisas basándote en documentos indexados.

Herramientas RAG:
- rag_search: Busca información relevante en documentos indexados
- rag_ingest_document: Indexa un nuevo documento al knowledge base
- rag_get_collection_stats: Ver estadísticas de colecciones

Flujo de trabajo:
1. Analiza la pregunta del usuario
2. Busca información relevante usando rag_search
3. Sintetiza la respuesta basándote únicamente en los documentos recuperados
4. Cita fuentes cuando sea posible

Reglas:
- Nunca inventes información que no esté en los documentos
- Si no hay información suficiente, indícalo claramente
- Prioriza la precisión sobre la completitud
- Mantén respuestas concisas y fundamentadas"""


# Skills para el RAG Agent
RAG_SKILLS = [
    Skill(
        id="document_search",
        name="Búsqueda Documental",
        description="Técnicas avanzadas de búsqueda semántica en documentos indexados"
    ),
    Skill(
        id="source_citation",
        name="Citación de Fuentes",
        description="Cómo citar correctamente fuentes documentales y atribuir información"
    ),
    Skill(
        id="uncertainty_handling",
        name="Manejo de Incertidumbre",
        description="Cómo manejar casos donde la información es incompleta o no se encuentra"
    )
]


class RagAgent(BaseSubAgent):
    """Subagente RAG: Responde preguntas basándose en documentos indexados."""

    id = "rag_agent"
    name = "RAG Specialist"
    description = "Especialista en Recuperación Aumentada: responde preguntas basándose en documentos indexados"
    version = "1.0.0"
    domain_tools = ["rag_search", "rag_ingest_document", "rag_get_collection_stats"]
    available_skills = RAG_SKILLS

    role = "Especialista en Recuperación de Información"
    expertise = "Experto en RAG (Retrieval Augmented Generation): búsqueda semántica, análisis documental y respuestas fundamentadas"
    task_requirements = "Pregunta sobre documentos indexados, o solicitud de indexar nuevos documentos"

    def __init__(self):
        super().__init__()
        self.system_prompt = _read_system_prompt()
        logger.info(f"📚 RagAgent initialized")

    async def execute(
        self,
        task: str,
        context: Optional[str] = None,
        llm_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_type: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> SubAgentResult:
        """Ejecuta usando LLM con herramientas RAG."""
        start_time = time.time()
        logger.info("📚 RagAgent executing", task=task[:100])

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
            logger.error(f"RagAgent error: {e}", exc_info=True)
            return SubAgentResult(
                success=False,
                response=f"❌ **Error en búsqueda RAG:** {str(e)}",
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
        """Ejecuta con LLM que decide qué herramientas RAG usar."""
        
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
        
        # Llamar a LLM con herramientas
        response = await call_llm_with_tools(
            llm_url=llm_url,
            model=model,
            messages=messages,
            tools=[t.to_function_schema() for t in tools],
            temperature=0.3,  # Baja temperatura para respuestas precisas
            provider_type=provider_type,
            api_key=api_key
        )
        
        # Procesar respuesta
        if hasattr(response, 'tool_calls') and response.tool_calls:
            # El LLM quiere usar herramientas
            results = []
            sources = []
            
            for tc in response.tool_calls:
                tool = next((t for t in tools if t.id == tc.function.name), None)
                if tool and tool.handler:
                    try:
                        import json
                        tool_params = json.loads(tc.function.arguments)
                        result = await tool.handler(**tool_params)
                        results.append({
                            "tool": tool.id,
                            "params": tool_params,
                            "result": result
                        })
                        
                        # Extraer fuentes si es una búsqueda
                        if tool.id == "rag_search" and result.get("success"):
                            for doc in result.get("results", []):
                                source = doc.get("metadata", {}).get("source", "Desconocido")
                                if source not in sources:
                                    sources.append(source)
                                    
                    except Exception as e:
                        logger.error(f"Error executing tool {tool.id}: {e}")
            
            # Segunda llamada para obtener respuesta final
            # Añadir resultados de herramientas al contexto
            tool_results_text = "\n\n".join([
                f"Resultado de {r['tool']}:\n{r['result'].get('context', str(r['result']))}"
                for r in results
            ])
            
            messages.append({"role": "assistant", "content": response.content or ""})
            messages.append({
                "role": "user",
                "content": f"Basándote en los resultados obtenidos:\n\n{tool_results_text}\n\nPor favor proporciona una respuesta completa y precisa a la pregunta original. Cita las fuentes cuando sea posible."
            })
            
            final_response = await call_llm_with_tools(
                llm_url=llm_url,
                model=model,
                messages=messages,
                tools=[],  # No más herramientas
                temperature=0.3,
                provider_type=provider_type,
                api_key=api_key
            )
            
            response_text = final_response.content
        else:
            # Respuesta directa sin herramientas
            response_text = response.content
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            "✅ RagAgent completed",
            execution_time_ms=execution_time_ms,
            response_length=len(response_text) if response_text else 0
        )
        
        return SubAgentResult(
            success=True,
            response=response_text or "No se pudo generar una respuesta.",
            agent_id=self.id,
            agent_name=self.name,
            tools_used=[r["tool"] for r in results] if 'results' in dir() else [],
            sources=sources if 'sources' in dir() else [],
            execution_time_ms=execution_time_ms
        )
