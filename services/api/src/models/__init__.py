"""
Modelos Pydantic para Brain API
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# ===========================================
# Enums
# ===========================================

class ExecutionStatus(str, Enum):
    """Estados posibles de una ejecución"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeType(str, Enum):
    """Tipos de nodos en un grafo"""
    ENTRY = "entry"
    EXIT = "exit"
    ACTION = "action"
    CONDITION = "condition"
    PARALLEL = "parallel"
    SUBGRAPH = "subgraph"


# ===========================================
# Graph Models
# ===========================================

class GraphNode(BaseModel):
    """Representa un nodo en un grafo de LangGraph"""
    id: str
    type: NodeType
    label: str
    description: Optional[str] = None
    config: Optional[dict[str, Any]] = None


class GraphEdge(BaseModel):
    """Representa una conexión entre nodos"""
    source: str
    target: str
    condition: Optional[str] = None
    label: Optional[str] = None


class Graph(BaseModel):
    """Representa un grafo completo de LangGraph"""
    id: str
    name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ===========================================
# Execution Models
# ===========================================

class ExecutionStep(BaseModel):
    """Representa un paso en la ejecución de un grafo"""
    step: int
    node_id: str
    timestamp: datetime
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    duration_ms: int
    error: Optional[str] = None


class Execution(BaseModel):
    """Representa una ejecución de un grafo"""
    id: str
    graph_id: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    input: dict[str, Any] = Field(default_factory=dict)
    output: Optional[dict[str, Any]] = None
    trace: list[ExecutionStep] = Field(default_factory=list)
    error: Optional[str] = None


# ===========================================
# RAG Models
# ===========================================

class Document(BaseModel):
    """Documento para RAG"""
    id: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    collection: str
    embedding: Optional[list[float]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SearchResult(BaseModel):
    """Resultado de búsqueda RAG"""
    document_id: str
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Respuesta de búsqueda RAG"""
    query: str
    results: list[SearchResult]
    total: int


# ===========================================
# Chain Models
# ===========================================

class ChainConfig(BaseModel):
    """Configuración de una cadena de LangChain"""
    id: str
    name: str
    description: Optional[str] = None
    chain_type: str
    config: dict[str, Any] = Field(default_factory=dict)


class ChainInvocation(BaseModel):
    """Invocación de una cadena"""
    chain_id: str
    input: dict[str, Any]
    output: Optional[dict[str, Any]] = None
    execution_time_ms: Optional[int] = None
    status: ExecutionStatus = ExecutionStatus.PENDING
