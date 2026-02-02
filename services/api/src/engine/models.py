"""
Modelos de datos para el motor de ejecución
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional, Callable, AsyncGenerator
from pydantic import BaseModel, Field
import uuid


class NodeType(str, Enum):
    """Tipos de nodos disponibles"""
    LLM = "llm"
    TOOL = "tool"
    RAG = "rag"
    CONDITION = "condition"
    HUMAN = "human"
    INPUT = "input"
    OUTPUT = "output"
    TRANSFORM = "transform"


class ExecutionStatus(str, Enum):
    """Estados de ejecución"""
    PENDING = "pending"
    RUNNING = "running"
    WAITING = "waiting"  # Esperando input humano
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeDefinition(BaseModel):
    """Definición de un nodo en el grafo"""
    id: str
    type: NodeType
    name: str
    config: dict[str, Any] = Field(default_factory=dict)
    
    # Para nodos LLM
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    prompt_template: Optional[str] = None  # ✅ NUEVO: Template con {{variables}}
    temperature: float = 0.7
    
    # Para nodos Tool
    tool_name: Optional[str] = None
    tool_config: Optional[dict] = None
    tools: list[str] = Field(default_factory=list)  # Lista de tools disponibles
    
    # Para nodos RAG
    collection: Optional[str] = None
    top_k: int = 5
    
    # Para nodos Condition
    condition_expr: Optional[str] = None


class EdgeDefinition(BaseModel):
    """Definición de una conexión entre nodos"""
    source: str
    target: str
    condition: Optional[str] = None  # Condición para seguir este edge


class ChainConfig(BaseModel):
    """Configuración de una cadena"""
    llm_provider_id: Optional[int] = None
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    system_prompt: Optional[str] = None
    
    # RAG config
    rag_collection: Optional[str] = None
    rag_top_k: int = 5
    
    # Memory config
    use_memory: bool = True
    memory_key: str = "chat_history"
    max_memory_messages: int = 20
    
    # Agent iteration config
    max_iterations: int = 15  # Límite de iteraciones del agente (configurable)
    ask_before_continue: bool = True  # Preguntar al usuario antes de superar el límite
    
    # Otros
    timeout: int = 300  # segundos
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChainDefinition(BaseModel):
    """Definición completa de una cadena/grafo"""
    id: str
    name: str
    description: Optional[str] = None
    type: str  # "agent" for Brain 2.0 agents
    version: str = "1.0.0"
    
    nodes: list[NodeDefinition] = Field(default_factory=list)
    edges: list[EdgeDefinition] = Field(default_factory=list)
    
    config: ChainConfig = Field(default_factory=ChainConfig)
    
    # Metadatos
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def get_node(self, node_id: str) -> Optional[NodeDefinition]:
        """
        Helper para obtener un nodo por ID.
        
        Args:
            node_id: ID del nodo a buscar
            
        Returns:
            NodeDefinition o None si no se encuentra
        """
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None


class ExecutionStep(BaseModel):
    """Un paso en la ejecución"""
    step_number: int
    node_id: str
    node_name: str
    node_type: NodeType
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    
    error: Optional[str] = None
    tokens_used: Optional[int] = None


class ExecutionState(BaseModel):
    """Estado actual de una ejecución"""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    chain_id: str
    chain_name: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    
    # Input/Output
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: Optional[dict[str, Any]] = None
    
    # Estado intermedio
    current_node: Optional[str] = None
    state: dict[str, Any] = Field(default_factory=dict)
    
    # Trace
    steps: list[ExecutionStep] = Field(default_factory=list)
    
    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Métricas
    total_tokens: int = 0
    total_duration_ms: int = 0
    
    # Error
    error: Optional[str] = None


class ExecutionResult(BaseModel):
    """Resultado final de una ejecución"""
    execution_id: str
    chain_id: str
    status: ExecutionStatus
    
    input_data: dict[str, Any]
    output_data: Optional[dict[str, Any]]
    
    steps: list[ExecutionStep]
    
    total_tokens: int
    total_duration_ms: int
    
    error: Optional[str] = None


class StreamEvent(BaseModel):
    """Evento de streaming durante la ejecución"""
    event_type: str  # "start", "node_start", "token", "node_end", "end", "error"
    execution_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Datos del evento
    node_id: Optional[str] = None
    node_name: Optional[str] = None
    content: Optional[str] = None
    data: dict[str, Any] = Field(default_factory=dict)


class ChainInvokeRequest(BaseModel):
    """Request para invocar una cadena"""
    input: dict[str, Any] = Field(default_factory=dict)
    config: Optional[ChainConfig] = None
    stream: bool = False
    
    # Override de LLM
    llm_provider_url: Optional[str] = None
    llm_provider_type: str = "ollama"  # "ollama", "openai", "anthropic", "groq", "azure"
    api_key: Optional[str] = None
    model: Optional[str] = None
    
    # Brain Events para Open WebUI
    emit_brain_events: bool = False


class ChainInvokeResponse(BaseModel):
    """Response de una invocación"""
    execution_id: str
    status: ExecutionStatus
    output: Optional[dict[str, Any]] = None
    error: Optional[str] = None
