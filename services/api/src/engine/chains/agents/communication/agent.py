"""
Communication Agent - Estratega de comunicación y storytelling.

Patrón: LLM-Only
Proporciona recomendaciones de comunicación usando LLM.
"""

import time
from pathlib import Path
from typing import Optional, Dict, Any

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
        return """Eres un Director de Comunicación experto en storytelling corporativo.

Ayudas a definir:
- Tono y estilo del mensaje según la audiencia
- Estructuras narrativas efectivas
- Arcos emocionales para conectar con la audiencia
- Mensajes clave y call-to-actions

Proporciona recomendaciones claras y accionables para comunicar efectivamente."""


# Skills simplificados para Communication
COMMUNICATION_SKILLS = [
    Skill(
        id="storytelling",
        name="Storytelling",
        description="Estructuras narrativas, tonos de comunicación, arcos emocionales"
    )
]


class CommunicationAgent(BaseSubAgent):
    """Estratega de comunicación usando LLM."""
    
    id = "communication_agent"
    name = "Communication Strategist"
    description = "Estratega de comunicación experto en storytelling y narrativa efectiva"
    version = "3.0.0"
    available_skills = COMMUNICATION_SKILLS
    domain_tools = []
    
    role = "Director de Comunicación"
    expertise = "Experto en comunicación estratégica y storytelling corporativo"
    task_requirements = "Describe qué necesitas comunicar y a qué audiencia"
    
    def __init__(self):
        super().__init__()
        self.system_prompt = _read_system_prompt()
        logger.info(f"💬 CommunicationAgent initialized")
    
    async def execute(
        self,
        task: str,
        context: Optional[str] = None,
        session_id: Optional[str] = None,
        llm_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_type: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ) -> SubAgentResult:
        """Ejecuta usando LLM para recomendaciones de comunicación."""
        start_time = time.time()
        logger.info("💬 CommunicationAgent executing", task=task[:80])
        
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
            logger.error(f"CommunicationAgent error: {e}", exc_info=True)
            return SubAgentResult(
                success=False,
                response=f"❌ **Error en comunicación:** {str(e)}",
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
        """Ejecuta con LLM para obtener recomendaciones."""
        
        # Obtener herramientas (aunque este agente no use tools de ejecución)
        tools = self.get_tools()
        
        # Construir mensajes
        system_content = self.system_prompt + self.get_skills_for_prompt()
        user_content = f"Tarea de comunicación: {task}"
        if context:
            user_content += f"\n\nContexto adicional: {context}"
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]
        
        # Llamar LLM
        response = await call_llm_with_tools(
            messages=messages,
            tools=[tool.to_function_schema() for tool in tools],
            temperature=0.7,
            provider_type=provider_type,
            api_key=api_key,
            llm_url=llm_url,
            model=model
        )
        
        # Retornar respuesta del LLM
        return SubAgentResult(
            success=True,
            response=response.content or "No se pudo generar respuesta",
            agent_id=self.id,
            agent_name=self.name,
            execution_time_ms=int((time.time() - start_time) * 1000)
        )


# Instancia para registro
communication_agent = CommunicationAgent()
