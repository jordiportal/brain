"""
MCP Models - Modelos de datos para conexiones MCP
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
import subprocess


class MCPConnectionType(str, Enum):
    """Tipos de conexión MCP"""
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"


@dataclass
class MCPTool:
    """Definición de una herramienta MCP"""
    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    
    def to_function_schema(self) -> Dict[str, Any]:
        """Convierte a formato de función para LLM"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema
            }
        }


@dataclass
class MCPResource:
    """Recurso expuesto por un servidor MCP"""
    uri: str
    name: str
    description: str = ""
    mime_type: str = "text/plain"


@dataclass
class MCPConnection:
    """Conexión a un servidor MCP"""
    id: str
    name: str
    conn_type: MCPConnectionType
    description: str = ""
    
    # Para conexión STDIO
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    
    # Para conexión HTTP/SSE
    server_url: Optional[str] = None
    
    # Configuración adicional
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Estado runtime (no persistido)
    process: Optional[subprocess.Popen] = field(default=None, repr=False)
    tools: List[MCPTool] = field(default_factory=list)
    resources: List[MCPResource] = field(default_factory=list)
    is_connected: bool = False
    server_info: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_strapi(cls, data: Dict[str, Any]) -> "MCPConnection":
        """Crear desde datos de Strapi"""
        conn_type = MCPConnectionType(data.get("type", "stdio"))
        
        return cls(
            id=data.get("documentId") or str(data.get("id")),
            name=data.get("name", ""),
            conn_type=conn_type,
            description=data.get("description", ""),
            command=data.get("command"),
            args=data.get("args") or [],
            env=data.get("env") or {},
            server_url=data.get("serverUrl"),
            config=data.get("config") or {}
        )
