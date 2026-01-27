"""
Brain 2.0 Tool Registry - Registro central de las 15 Core Tools

Core Tools:
- Filesystem (5): read, write, edit, list, search
- Execution (3): shell, python, javascript
- Web (2): web_search, web_fetch
- Reasoning (4): think, reflect, plan, finish
- Utils (1): calculate
"""

import structlog
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = structlog.get_logger()


class ToolType(str, Enum):
    """Tipos de herramientas disponibles"""
    CORE = "core"       # Las 15 core tools de Brain 2.0
    BUILTIN = "builtin" # Alias para compatibilidad (=CORE)
    OPENAPI = "openapi" # Compatibilidad Brain 1.x
    MCP = "mcp"         # Compatibilidad Brain 1.x
    CUSTOM = "custom"   # Compatibilidad Brain 1.x


@dataclass
class ToolDefinition:
    """Definición de una herramienta"""
    id: str
    name: str
    description: str
    type: ToolType
    parameters: Dict[str, Any] = field(default_factory=dict)
    handler: Optional[Callable] = None
    # Compatibilidad Brain 1.x
    openapi_tool: Optional[Any] = None
    mcp_server: Optional[str] = None
    mcp_tool_name: Optional[str] = None
    
    def to_function_schema(self) -> Dict[str, Any]:
        """Convierte a schema de función para el LLM (formato OpenAI)"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


class ToolRegistry:
    """
    Registro central de herramientas Brain 2.0
    
    Solo registra las 15 core tools nativas.
    """
    
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self._core_registered = False
    
    def register(self, tool: ToolDefinition) -> None:
        """Registra una herramienta"""
        self.tools[tool.id] = tool
        logger.debug(f"Tool registrada: {tool.id}")
    
    def register_core_tool(
        self,
        id: str,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable
    ) -> None:
        """Registra una core tool"""
        tool = ToolDefinition(
            id=id,
            name=name,
            description=description,
            type=ToolType.CORE,
            parameters=parameters,
            handler=handler
        )
        self.register(tool)
    
    def get(self, tool_id: str) -> Optional[ToolDefinition]:
        """Obtiene una herramienta por ID"""
        return self.tools.get(tool_id)
    
    def list(self, tool_type: Optional[ToolType] = None) -> List[ToolDefinition]:
        """Lista herramientas, opcionalmente filtradas por tipo"""
        if tool_type:
            return [t for t in self.tools.values() if t.type == tool_type]
        return list(self.tools.values())
    
    def get_tools_for_llm(self, tool_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Obtiene las herramientas en formato para el LLM.
        
        Args:
            tool_ids: Lista de IDs específicos, o None para todas
        
        Returns:
            Lista de schemas de función en formato OpenAI
        """
        if tool_ids:
            tools = [self.tools[tid] for tid in tool_ids if tid in self.tools]
        else:
            tools = list(self.tools.values())
        
        return [tool.to_function_schema() for tool in tools]
    
    def get_all_tool_names(self) -> List[str]:
        """Obtiene lista de nombres de todas las herramientas"""
        return list(self.tools.keys())
    
    async def execute(self, tool_id: str, **kwargs) -> Dict[str, Any]:
        """
        Ejecuta una herramienta por ID.
        
        Args:
            tool_id: ID de la herramienta
            **kwargs: Argumentos para la herramienta
        
        Returns:
            Resultado de la herramienta
        """
        tool = self.get(tool_id)
        if not tool:
            return {"error": f"Herramienta no encontrada: {tool_id}", "success": False}
        
        if not tool.handler:
            return {"error": f"Herramienta sin handler: {tool_id}", "success": False}
        
        try:
            # Filtrar kwargs para solo incluir parámetros válidos del schema
            valid_params = self._filter_valid_params(tool, kwargs)
            
            result = tool.handler(**valid_params)
            
            # Si es coroutine, await
            if hasattr(result, '__await__'):
                result = await result
            
            # Si el resultado ya tiene estructura, retornarlo
            if isinstance(result, dict):
                return result
            
            # Sino, envolverlo
            return {"success": True, "data": result}
            
        except Exception as e:
            logger.error(f"Error ejecutando tool {tool_id}: {e}", exc_info=True)
            return {"error": str(e), "success": False}
    
    def _filter_valid_params(self, tool: ToolDefinition, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filtra los parámetros para incluir solo los definidos en el schema.
        
        Esto previene errores cuando el LLM inventa parámetros que no existen.
        """
        # Obtener propiedades válidas del schema
        valid_props = set()
        if tool.parameters and "properties" in tool.parameters:
            valid_props = set(tool.parameters["properties"].keys())
        
        if not valid_props:
            # Si no hay schema definido, pasar todos los kwargs
            return kwargs
        
        # Filtrar solo parámetros válidos
        filtered = {}
        invalid = []
        
        for key, value in kwargs.items():
            if key in valid_props:
                filtered[key] = value
            else:
                invalid.append(key)
        
        if invalid:
            logger.warning(
                f"Ignorando parámetros inválidos para {tool.id}: {invalid}",
                tool_id=tool.id,
                invalid_params=invalid
            )
        
        return filtered
    
    def register_core_tools(self) -> None:
        """
        Registra las 15 Core Tools de Brain 2.0
        
        Filesystem (5): read, write, edit, list, search
        Execution (3): shell, python, javascript
        Web (2): web_search, web_fetch
        Reasoning (4): think, reflect, plan, finish
        Utils (1): calculate
        """
        if self._core_registered:
            return
        
        # Importar core tools
        from .core import CORE_TOOLS
        
        # Registrar cada tool
        for tool_id, tool_def in CORE_TOOLS.items():
            self.register_core_tool(
                id=tool_def["id"],
                name=tool_def["name"],
                description=tool_def["description"],
                parameters=tool_def["parameters"],
                handler=tool_def["handler"]
            )
        
        self._core_registered = True
        
        # Log de herramientas registradas
        tool_names = list(CORE_TOOLS.keys())
        logger.info(
            f"✅ Brain 2.0 Core Tools registradas: {len(tool_names)}",
            tools=tool_names
        )
    
    def get_tools_summary(self) -> str:
        """
        Genera un resumen de las herramientas disponibles para prompts.
        """
        if not self.tools:
            return "No hay herramientas disponibles."
        
        lines = ["Herramientas disponibles:"]
        
        # Agrupar por categoría
        categories = {
            "Filesystem": ["read", "write", "edit", "list", "search"],
            "Execution": ["shell", "python", "javascript"],
            "Web": ["web_search", "web_fetch"],
            "Reasoning": ["think", "reflect", "plan", "finish"],
            "Utils": ["calculate"]
        }
        
        for category, tool_ids in categories.items():
            category_tools = [self.tools[tid] for tid in tool_ids if tid in self.tools]
            if category_tools:
                lines.append(f"\n{category}:")
                for tool in category_tools:
                    lines.append(f"  - {tool.name}: {tool.description[:80]}...")
        
        return "\n".join(lines)


# Instancia global
tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """Obtiene el registry global de herramientas"""
    return tool_registry


# ============================================
# Compatibilidad con Brain 1.x
# ============================================

# Alias para compatibilidad hacia atrás
ToolRegistry.register_builtin_tools = ToolRegistry.register_core_tools

# Método stub para load_openapi_tools (ya no se usa en Brain 2.0)
async def _load_openapi_tools_stub(self) -> int:
    """Stub para compatibilidad - OpenAPI tools deshabilitadas en Brain 2.0"""
    logger.info("OpenAPI tools disabled in Brain 2.0 - using core tools only")
    return 0

ToolRegistry.load_openapi_tools = _load_openapi_tools_stub
