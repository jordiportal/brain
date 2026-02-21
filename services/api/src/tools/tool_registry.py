"""
Brain 2.0 Tool Registry - Registro central de Core Tools

Core Tools:
- Filesystem (5): read_file, write_file, edit_file, list_directory, search_files
- Execution (3): shell, python, javascript
- Web (2): web_search, web_fetch
- Reasoning (4): think, reflect, plan, finish
- Utils (1): calculate
- Delegation (2): get_agent_info, delegate
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
    DOMAIN = "domain"   # Herramientas específicas de subagentes (media, web, etc.)
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
    
    def register_domain_tool(
        self,
        id: str,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable
    ) -> None:
        """Registra una domain tool (herramienta específica de subagente)"""
        tool = ToolDefinition(
            id=id,
            name=name,
            description=description,
            type=ToolType.DOMAIN,
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

    # IDs de tools para el Adaptive Agent (sin consult_team_member)
    ADAPTIVE_TOOL_IDS = [
        "read_file", "write_file", "edit_file", "list_directory", "search_files",
        "shell", "python", "javascript",
        "web_search", "web_fetch",
        "think", "reflect", "plan", "finish",
        "calculate",
        "get_agent_info", "delegate", "parallel_delegate",
        "user_tasks_list", "user_tasks_create", "user_tasks_update",
        "user_tasks_delete", "user_tasks_run_now", "user_tasks_results",
    ]

    def get_tools_for_team(self) -> List[Dict[str, Any]]:
        """
        Herramientas para el coordinador Brain Team: cognición + consulta + ejecución.
        
        consult_team_member: pedir opiniones. delegate: ejecutar la tarea con el experto elegido
        (ej. generar presentación con designer_agent tras el consenso).
        """
        team_ids = [
            "think", "reflect", "plan", "finish",
            "get_agent_info", "consult_team_member", "delegate"
        ]
        return self.get_tools_for_llm(team_ids)
    
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
        NOTA: Los parámetros que empiezan con _ son internos del sistema y siempre se pasan.
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
            # Parámetros internos (con _) siempre se pasan
            if key.startswith("_"):
                filtered[key] = value
            elif key in valid_props:
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
        Registra las Core Tools de Brain 2.0, Team tools y Domain tools.
        
        Core: Filesystem (5), Execution (3), Web (2), Reasoning (4), Utils (1), Delegation (2)
        Team: consult_team_member (solo para cadena Brain Team)
        Domain: Media (generate_image, analyze_image), Slides (generate_slides), SAP BIW
        """
        if self._core_registered:
            return
        
        # Importar core y team tools
        from .core import CORE_TOOLS, TEAM_TOOLS, SLIDES_TOOLS
        from .domains.media import MEDIA_TOOLS
        from .domains.sap_biw import BIW_TOOLS
        from .domains.microsoft365 import M365_TOOLS
        from .domains.user_tasks import USER_TASKS_TOOLS
        
        # Registrar cada core tool (delegation tools son callables para enum dinámico)
        for tool_id, tool_def in CORE_TOOLS.items():
            td = tool_def() if callable(tool_def) else tool_def
            self.register_core_tool(
                id=td["id"],
                name=td["name"],
                description=td["description"],
                parameters=td["parameters"],
                handler=td["handler"]
            )
        
        # Registrar team tools
        for tool_id, tool_def in TEAM_TOOLS.items():
            td = tool_def() if callable(tool_def) else tool_def
            self.register_core_tool(
                id=td["id"],
                name=td["name"],
                description=td["description"],
                parameters=td["parameters"],
                handler=td["handler"]
            )
        
        # Registrar domain tools: Media
        for tool_id, tool_def in MEDIA_TOOLS.items():
            td = tool_def() if callable(tool_def) else tool_def
            self.register_domain_tool(
                id=td["id"],
                name=td["name"],
                description=td["description"],
                parameters=td["parameters"],
                handler=td["handler"]
            )
        
        # Registrar domain tools: Slides
        for tool_id, tool_def in SLIDES_TOOLS.items():
            td = tool_def() if callable(tool_def) else tool_def
            self.register_domain_tool(
                id=td["id"],
                name=td["name"],
                description=td["description"],
                parameters=td["parameters"],
                handler=td["handler"]
            )
        
        # Registrar domain tools: SAP BIW
        for tool_id, tool_def in BIW_TOOLS.items():
            td = tool_def() if callable(tool_def) else tool_def
            self.register_domain_tool(
                id=td["id"],
                name=td["name"],
                description=td["description"],
                parameters=td["parameters"],
                handler=td["handler"]
            )
        
        # Registrar domain tools: Microsoft 365
        for tool_id, tool_def in M365_TOOLS.items():
            td = tool_def() if callable(tool_def) else tool_def
            self.register_domain_tool(
                id=td["id"],
                name=td["name"],
                description=td["description"],
                parameters=td["parameters"],
                handler=td["handler"]
            )
        
        # Registrar domain tools: User Tasks
        for tool_id, tool_def in USER_TASKS_TOOLS.items():
            td = tool_def() if callable(tool_def) else tool_def
            self.register_domain_tool(
                id=td["id"],
                name=td["name"],
                description=td["description"],
                parameters=td["parameters"],
                handler=td["handler"]
            )
        
        # Registrar domain tools: RAG
        from .domains.rag import RAG_TOOLS
        for tool_id, tool_def in RAG_TOOLS.items():
            td = tool_def() if callable(tool_def) else tool_def
            self.register_domain_tool(
                id=td["id"],
                name=td["name"],
                description=td["description"],
                parameters=td["parameters"],
                handler=td["handler"]
            )
        
        # Registrar domain tools: Office
        from .domains.office import OFFICE_TOOLS
        for tool_id, tool_def in OFFICE_TOOLS.items():
            td = tool_def() if callable(tool_def) else tool_def
            self.register_domain_tool(
                id=td["id"],
                name=td["name"],
                description=td["description"],
                parameters=td["parameters"],
                handler=td["handler"]
            )
        
        self._core_registered = True
        
        # Log de herramientas registradas
        all_tools = list(CORE_TOOLS.keys()) + list(TEAM_TOOLS.keys()) + list(MEDIA_TOOLS.keys()) + list(SLIDES_TOOLS.keys()) + list(BIW_TOOLS.keys()) + list(M365_TOOLS.keys()) + list(USER_TASKS_TOOLS.keys()) + list(RAG_TOOLS.keys()) + list(OFFICE_TOOLS.keys())
        logger.info(
            f"✅ Brain 2.0 Tools registradas: {len(all_tools)}",
            tools=all_tools
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
            "Filesystem": ["read_file", "write_file", "edit_file", "list_directory", "search_files"],
            "Execution": ["shell", "python", "javascript"],
            "Web": ["web_search", "web_fetch"],
            "Reasoning": ["think", "reflect", "plan", "finish"],
            "Utils": ["calculate"],
            "Delegation": ["get_agent_info", "delegate", "parallel_delegate"]
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


async def _load_openapi_tools(self) -> int:
    """
    Carga herramientas OpenAPI desde las conexiones activas en BD.
    
    Las tools se registran con ToolType.OPENAPI y quedan disponibles
    en el registry global. Los BIW domain tools las detectan
    automaticamente y delegan en ellas si existen.
    """
    from .openapi_tools import openapi_toolkit
    
    try:
        conn_count = await openapi_toolkit.load_connections_from_db()
        if conn_count == 0:
            logger.info("No hay conexiones OpenAPI activas en BD")
            return 0
        
        all_tools = await openapi_toolkit.load_all_tools()
        
        # Registrar cada tool OpenAPI en el registry
        registered = 0
        for tool_id, oapi_tool in all_tools.items():
            tool_def = ToolDefinition(
                id=oapi_tool.id,
                name=oapi_tool.name,
                description=oapi_tool.description,
                type=ToolType.OPENAPI,
                parameters=oapi_tool.to_function_schema().get("parameters", {}),
                handler=oapi_tool.execute,
                openapi_tool=oapi_tool
            )
            self.register(tool_def)
            registered += 1
        
        logger.info(f"✅ OpenAPI tools registradas: {registered} (de {conn_count} conexiones)")
        return registered
        
    except Exception as e:
        logger.error(f"Error cargando OpenAPI tools: {e}", exc_info=True)
        return 0


ToolRegistry.load_openapi_tools = _load_openapi_tools
