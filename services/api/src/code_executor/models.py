"""
Code Executor - Modelos de datos
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum


class Language(str, Enum):
    """Lenguajes soportados"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    NODE = "node"  # Alias para javascript


class ExecutionStatus(str, Enum):
    """Estados de ejecución"""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CONTAINER_ERROR = "container_error"


@dataclass
class ExecutionResult:
    """Resultado de una ejecución de código"""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float  # en segundos
    status: ExecutionStatus
    language: Language
    error_message: Optional[str] = None
    container_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario"""
        return {
            "success": self.success,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "execution_time": self.execution_time,
            "status": self.status.value,
            "language": self.language.value,
            "error_message": self.error_message,
            "container_id": self.container_id
        }


@dataclass
class ExecutionConfig:
    """Configuración de ejecución"""
    timeout: int = 30  # segundos
    memory_limit: str = "512m"
    cpu_limit: float = 1.0
    network_disabled: bool = True
    auto_remove: bool = True
