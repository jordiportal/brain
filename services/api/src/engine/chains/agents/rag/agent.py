"""
RAG Agent - Subagente de Recuperación Aumentada

Usa el mismo bucle iterativo que el agente principal (run_session_loop).
Responde preguntas basándose en documentos indexados en el knowledge base RAG.
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
        logger.info("📚 RagAgent initialized (shared loop)")

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
        logger.info("📚 RagAgent executing", task=task[:100])
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
            logger.error(f"RagAgent error: {e}", exc_info=True)
            return SubAgentResult(
                success=False,
                response=f"❌ **Error en búsqueda RAG:** {str(e)}",
                agent_id=self.id,
                agent_name=self.name,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
