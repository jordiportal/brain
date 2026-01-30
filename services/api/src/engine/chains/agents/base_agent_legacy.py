"""
Base Subagent - Clase base para todos los subagentes especializados

Define la interfaz común y el comportamiento base para subagentes
de dominio específico (media, sap, mail, office, etc.)
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime

import structlog

from src.tools import tool_registry, ToolDefinition

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
    
    Cada subagente:
    - Tiene un ID único y descripción
    - Define las tools de su dominio
    - Tiene un system prompt especializado
    - Implementa execute() para procesar tareas
    """
    
    # Atributos que deben definir las subclases
    id: str = "base_agent"
    name: str = "Base Agent"
    description: str = "Base agent for specialization"
    version: str = "1.0.0"
    
    # Tools de dominio (IDs de tools que este agente puede usar)
    domain_tools: List[str] = []
    
    # System prompt especializado
    system_prompt: str = "You are a specialized agent."
    
    def __init__(self):
        """Inicializa el subagente."""
        self._registered_at = datetime.now()
        logger.info(
            f"🤖 SubAgent initialized",
            agent_id=self.id,
            tools=self.domain_tools
        )
    
    def get_tools(self) -> List[ToolDefinition]:
        """
        Obtiene las definiciones de tools de este dominio.
        
        Returns:
            Lista de ToolDefinition para las tools del dominio
        """
        tools = []
        for tool_id in self.domain_tools:
            tool = tool_registry.get(tool_id)
            if tool:
                tools.append(tool)
            else:
                logger.warning(f"Tool not found: {tool_id}")
        return tools
    
    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        """
        Obtiene tools en formato para el LLM (function calling).
        
        Returns:
            Lista de schemas de función para el LLM
        """
        tools = self.get_tools()
        return [tool.to_function_schema() for tool in tools]
    
    def get_tools_description(self) -> str:
        """
        Genera descripción de tools para incluir en prompts.
        
        Returns:
            String con la descripción de cada tool
        """
        tools = self.get_tools()
        descriptions = []
        for tool in tools:
            params = tool.parameters.get("properties", {})
            params_str = ", ".join(params.keys())
            descriptions.append(f"- {tool.name}({params_str}): {tool.description}")
        return "\n".join(descriptions)
    
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
        """
        Ejecuta una tarea con las herramientas del dominio.
        
        Args:
            task: Descripción de la tarea a realizar
            context: Contexto adicional o resultados de pasos previos
            llm_url: URL del LLM
            model: Modelo a usar
            provider_type: Tipo de proveedor (ollama, openai, etc.)
            api_key: API key si es necesaria
        
        Returns:
            SubAgentResult con el resultado de la ejecución
        """
        pass
    
    async def stream_execute(
        self,
        task: str,
        context: Optional[str] = None,
        llm_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_type: str = "ollama",
        api_key: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Ejecuta una tarea con streaming de eventos.
        
        Por defecto, llama a execute() y emite el resultado.
        Subclases pueden override para streaming real.
        """
        result = await self.execute(
            task=task,
            context=context,
            llm_url=llm_url,
            model=model,
            provider_type=provider_type,
            api_key=api_key
        )
        
        # Emitir resultado como evento
        yield {
            "event_type": "subagent_result",
            "agent_id": self.id,
            "data": result.to_dict()
        }
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}, tools={len(self.domain_tools)})>"


class SubAgentRegistry:
    """
    Registry de subagentes disponibles.
    
    Permite registrar, obtener y listar subagentes especializados.
    """
    
    def __init__(self):
        self._agents: Dict[str, BaseSubAgent] = {}
        self._initialized = False
    
    def register(self, agent: BaseSubAgent) -> None:
        """
        Registra un subagente.
        
        Args:
            agent: Instancia del subagente a registrar
        """
        if agent.id in self._agents:
            logger.warning(f"Overwriting existing agent: {agent.id}")
        
        self._agents[agent.id] = agent
        logger.info(
            f"✅ SubAgent registered",
            agent_id=agent.id,
            name=agent.name,
            tools=agent.domain_tools
        )
    
    def get(self, agent_id: str) -> Optional[BaseSubAgent]:
        """
        Obtiene un subagente por ID.
        
        Args:
            agent_id: ID del subagente
            
        Returns:
            El subagente o None si no existe
        """
        return self._agents.get(agent_id)
    
    def list(self) -> List[BaseSubAgent]:
        """
        Lista todos los subagentes registrados.
        
        Returns:
            Lista de subagentes
        """
        return list(self._agents.values())
    
    def list_ids(self) -> List[str]:
        """
        Lista los IDs de subagentes disponibles.
        
        Returns:
            Lista de IDs
        """
        return list(self._agents.keys())
    
    def get_description(self) -> str:
        """
        Genera descripción de todos los subagentes para prompts.
        
        Returns:
            String con descripción de cada subagente
        """
        descriptions = []
        for agent in self._agents.values():
            tools_str = ", ".join(agent.domain_tools)
            descriptions.append(
                f"- {agent.id}: {agent.description}\n  Tools: [{tools_str}]"
            )
        return "\n".join(descriptions)
    
    def is_initialized(self) -> bool:
        """Verifica si hay subagentes registrados."""
        return len(self._agents) > 0


# Singleton del registry
subagent_registry = SubAgentRegistry()
