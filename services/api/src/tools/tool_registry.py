"""
Tool Registry - Registro central de herramientas para agentes
"""

import structlog
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum

from .openapi_tools import OpenAPITool, openapi_toolkit

logger = structlog.get_logger()


class ToolType(str, Enum):
    """Tipos de herramientas disponibles"""
    OPENAPI = "openapi"
    MCP = "mcp"
    BUILTIN = "builtin"
    CUSTOM = "custom"


@dataclass
class ToolDefinition:
    """Definición de una herramienta"""
    id: str
    name: str
    description: str
    type: ToolType
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Para tools builtin/custom
    handler: Optional[Callable] = None
    
    # Para tools OpenAPI
    openapi_tool: Optional[OpenAPITool] = None
    
    # Para tools MCP
    mcp_server: Optional[str] = None
    mcp_tool_name: Optional[str] = None
    
    def to_function_schema(self) -> Dict[str, Any]:
        """Convierte a schema de función para el LLM"""
        if self.openapi_tool:
            return self.openapi_tool.to_function_schema()
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class ToolRegistry:
    """Registro central de todas las herramientas"""
    
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self._builtin_registered = False
    
    def register(self, tool: ToolDefinition) -> None:
        """Registra una herramienta"""
        self.tools[tool.id] = tool
        logger.debug(f"Tool registrada: {tool.id} ({tool.type})")
    
    def register_builtin(
        self,
        id: str,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable
    ) -> None:
        """Registra una herramienta builtin"""
        tool = ToolDefinition(
            id=id,
            name=name,
            description=description,
            type=ToolType.BUILTIN,
            parameters=parameters,
            handler=handler
        )
        self.register(tool)
    
    def register_openapi_tool(self, openapi_tool: OpenAPITool) -> None:
        """Registra una herramienta OpenAPI"""
        tool = ToolDefinition(
            id=openapi_tool.id,
            name=openapi_tool.name,
            description=openapi_tool.description,
            type=ToolType.OPENAPI,
            openapi_tool=openapi_tool
        )
        self.register(tool)
    
    async def load_openapi_tools(self) -> int:
        """Carga todas las herramientas OpenAPI"""
        tools = await openapi_toolkit.load_all_tools()
        
        for tool in tools.values():
            self.register_openapi_tool(tool)
        
        return len(tools)
    
    def get(self, tool_id: str) -> Optional[ToolDefinition]:
        """Obtiene una herramienta por ID"""
        return self.tools.get(tool_id)
    
    def list(self, tool_type: Optional[ToolType] = None) -> List[ToolDefinition]:
        """Lista herramientas, opcionalmente filtradas por tipo"""
        if tool_type:
            return [t for t in self.tools.values() if t.type == tool_type]
        return list(self.tools.values())
    
    def get_tools_for_llm(self, tool_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Obtiene las herramientas en formato para el LLM"""
        if tool_ids:
            tools = [self.tools[tid] for tid in tool_ids if tid in self.tools]
        else:
            tools = list(self.tools.values())
        
        return [tool.to_function_schema() for tool in tools]
    
    async def execute(self, tool_id: str, **kwargs) -> Dict[str, Any]:
        """Ejecuta una herramienta"""
        tool = self.get(tool_id)
        if not tool:
            return {"error": f"Herramienta no encontrada: {tool_id}"}
        
        try:
            if tool.type == ToolType.OPENAPI and tool.openapi_tool:
                return await tool.openapi_tool.execute(**kwargs)
            
            elif tool.type == ToolType.BUILTIN and tool.handler:
                result = tool.handler(**kwargs)
                # Si es async, await
                if hasattr(result, '__await__'):
                    result = await result
                return {"success": True, "data": result}
            
            elif tool.type == ToolType.MCP:
                # TODO: Implementar ejecución MCP
                return {"error": "MCP tools no implementado aún"}
            
            else:
                return {"error": f"No se puede ejecutar tool de tipo {tool.type}"}
                
        except Exception as e:
            logger.error(f"Error ejecutando tool {tool_id}: {e}")
            return {"error": str(e), "success": False}
    
    def register_builtin_tools(self) -> None:
        """Registra las herramientas builtin por defecto"""
        if self._builtin_registered:
            return
        
        # Calculator
        self.register_builtin(
            id="calculator",
            name="calculator",
            description="Realiza cálculos matemáticos. Soporta operaciones básicas (+, -, *, /) y funciones como sqrt, pow, sin, cos.",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Expresión matemática a evaluar, ej: '2 + 2', 'sqrt(16)', 'pow(2, 8)'"
                    }
                },
                "required": ["expression"]
            },
            handler=self._builtin_calculator
        )
        
        # Current DateTime
        self.register_builtin(
            id="current_datetime",
            name="current_datetime",
            description="Obtiene la fecha y hora actual del sistema.",
            parameters={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "description": "Formato de fecha (opcional). Por defecto ISO 8601."
                    }
                },
                "required": []
            },
            handler=self._builtin_datetime
        )
        
        self._builtin_registered = True
        logger.info("Tools builtin registradas")
    
    def _builtin_calculator(self, expression: str) -> Dict[str, Any]:
        """Calculadora básica"""
        import math
        
        # Funciones permitidas
        allowed = {
            'sqrt': math.sqrt,
            'pow': pow,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'log': math.log,
            'log10': math.log10,
            'abs': abs,
            'round': round,
            'pi': math.pi,
            'e': math.e
        }
        
        try:
            # Evaluar expresión de forma segura
            result = eval(expression, {"__builtins__": {}}, allowed)
            return {"result": result, "expression": expression}
        except Exception as e:
            return {"error": str(e), "expression": expression}
    
    def _builtin_datetime(self, format: str = None) -> Dict[str, Any]:
        """Obtiene fecha/hora actual"""
        from datetime import datetime
        
        now = datetime.now()
        
        if format:
            try:
                formatted = now.strftime(format)
                return {"datetime": formatted, "format": format}
            except:
                pass
        
        return {
            "datetime": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timestamp": now.timestamp()
        }


# Instancia global
tool_registry = ToolRegistry()
