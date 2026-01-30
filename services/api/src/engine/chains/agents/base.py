"""
Base Subagent - Clase base simplificada para subagentes especializados.

Define la interfaz común y el registry para subagentes de dominio
(media, slides, sap, mail, office, etc.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

import structlog

logger = structlog.get_logger()


@dataclass
class SubAgentResult:
    """Resultado de la ejecución de un subagente."""
    
    success: bool
    response: str
    agent_id: str
    agent_name: str
    tools_used: List[str] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time_ms: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            "success": self.success,
            "response": self.response,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "tools_used": self.tools_used,
            "images": self.images,
            "sources": self.sources,
            "data": self.data,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "has_images": len(self.images) > 0,
            "has_sources": len(self.sources) > 0
        }


class BaseSubAgent(ABC):
    """
    Clase base abstracta para subagentes especializados.
    
    Cada subagente define:
    - id, name, description: Identificación
    - role: Rol profesional del subagente (ej: "Diseñador Visual")
    - expertise: Áreas de expertise para consultas
    - task_requirements: Qué necesita recibir para ejecutar
    - domain_tools: Lista de IDs de herramientas del dominio
    - system_prompt: Prompt de sistema
    - execute(): Método principal de ejecución
    - consult(): Método para consultas de expertise (opcional)
    """
    
    id: str = "base_agent"
    name: str = "Base Agent"
    description: str = "Base agent"
    version: str = "1.0.0"
    domain_tools: List[str] = []
    system_prompt: str = "You are a specialized agent."
    
    # Rol y expertise del subagente
    role: str = "Especialista"
    expertise: str = "Puedo ayudarte con tareas de mi dominio."
    
    # Qué necesita para ejecutar
    task_requirements: str = "Descripción de la tarea a realizar."
    
    def __init__(self):
        logger.info(f"🤖 SubAgent initialized: {self.id} ({self.role})")
    
    async def consult(
        self,
        topic: str,
        context: Optional[str] = None,
        llm_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_type: str = "openai",
        api_key: Optional[str] = None
    ) -> SubAgentResult:
        """
        Consulta al subagente para obtener recomendaciones de su expertise.
        Por defecto, usa el LLM para generar una respuesta consultiva.
        Los subagentes pueden sobrescribir este método.
        """
        from ..llm_utils import call_llm_with_tools
        
        consult_prompt = f"""Eres {self.role}. {self.expertise}

Un colega te consulta sobre: {topic}

{f"Contexto adicional: {context}" if context else ""}

Responde de forma breve y profesional:
1. Da tu opinión experta sobre el enfoque
2. Sugiere 2-3 opciones o estilos que podrían funcionar
3. Haz una pregunta para afinar tu propuesta (opcional)

Sé conciso pero útil. Responde en español."""

        try:
            response = await call_llm_with_tools(
                messages=[
                    {"role": "system", "content": f"Eres {self.role}. Responde de forma concisa y profesional."},
                    {"role": "user", "content": consult_prompt}
                ],
                tools=[],
                temperature=0.7,
                provider_type=provider_type,
                api_key=api_key,
                llm_url=llm_url,
                model=model
            )
            
            return SubAgentResult(
                success=True,
                response=response.content or "Sin respuesta",
                agent_id=self.id,
                agent_name=self.name,
                data={"mode": "consult", "topic": topic}
            )
        except Exception as e:
            logger.error(f"Consult error: {e}")
            return SubAgentResult(
                success=False,
                response=f"Error en consulta: {str(e)}",
                agent_id=self.id,
                agent_name=self.name,
                error=str(e)
            )
    
    def get_tools(self) -> List[Any]:
        """Obtiene las definiciones de tools de este dominio."""
        from src.tools import tool_registry
        
        tools = []
        for tool_id in self.domain_tools:
            tool = tool_registry.get(tool_id)
            if tool:
                tools.append(tool)
        return tools
    
    @abstractmethod
    async def execute(
        self,
        task: str,
        context: Optional[str] = None,
        llm_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_type: str = "ollama",
        api_key: Optional[str] = None
    ) -> SubAgentResult:
        """Ejecuta una tarea."""
        pass


class SubAgentRegistry:
    """Registry singleton de subagentes disponibles."""
    
    def __init__(self):
        self._agents: Dict[str, BaseSubAgent] = {}
    
    def register(self, agent: BaseSubAgent) -> None:
        """Registra un subagente."""
        self._agents[agent.id] = agent
        logger.info(f"✅ SubAgent registered: {agent.id}")
    
    def get(self, agent_id: str) -> Optional[BaseSubAgent]:
        """Obtiene un subagente por ID."""
        return self._agents.get(agent_id)
    
    def list_ids(self) -> List[str]:
        """Lista los IDs disponibles."""
        return list(self._agents.keys())
    
    def list(self) -> List[BaseSubAgent]:
        """Lista todos los subagentes."""
        return list(self._agents.values())
    
    def is_initialized(self) -> bool:
        """Verifica si hay subagentes registrados."""
        return len(self._agents) > 0
    
    def get_description(self) -> str:
        """Descripción de todos los subagentes para prompts."""
        return "\n".join(
            f"- {a.id}: {a.description}"
            for a in self._agents.values()
        )


# Singleton
subagent_registry = SubAgentRegistry()
