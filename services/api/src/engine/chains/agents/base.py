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
    - task_requirements: Qué necesita recibir para ejecutar (autodescripción)
    - domain_tools: Lista de IDs de herramientas del dominio
    - system_prompt: Prompt de sistema (opcional)
    - execute(): Método principal de ejecución
    """
    
    id: str = "base_agent"
    name: str = "Base Agent"
    description: str = "Base agent"
    version: str = "1.0.0"
    domain_tools: List[str] = []
    system_prompt: str = "You are a specialized agent."
    
    # NUEVO: El subagente describe qué necesita recibir
    task_requirements: str = "Descripción de la tarea a realizar."
    
    def __init__(self):
        logger.info(f"🤖 SubAgent initialized: {self.id}")
    
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
