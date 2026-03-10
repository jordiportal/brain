"""
Brain Engine - Motor de ejecución de cadenas y grafos LangGraph
"""

from .executor import ChainExecutor
from .registry import ChainRegistry, chain_registry
from .models import (
    # v2 Task-centric models
    Task,
    TaskState,
    TaskEvent,
    TaskFilters,
    Message,
    Part,
    Artifact,
    AgentState,
    TERMINAL_STATES,
    ACTIVE_STATES,
    VALID_TRANSITIONS,
    # Legacy models (still used by existing code)
    ChainDefinition,
    ChainConfig,
    NodeDefinition,
    ExecutionState,
    ExecutionResult,
    StreamEvent,
)

__all__ = [
    # v2
    "Task",
    "TaskState",
    "TaskEvent",
    "TaskFilters",
    "Message",
    "Part",
    "Artifact",
    "AgentState",
    "TERMINAL_STATES",
    "ACTIVE_STATES",
    "VALID_TRANSITIONS",
    # Legacy
    "ChainExecutor",
    "ChainRegistry",
    "chain_registry",
    "ChainDefinition",
    "ChainConfig",
    "NodeDefinition",
    "ExecutionState",
    "ExecutionResult",
    "StreamEvent",
]
