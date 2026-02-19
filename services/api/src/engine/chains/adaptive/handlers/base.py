"""
Clase base para handlers de tools.

Cada handler encapsula:
- Preparación de argumentos
- Ejecución de la tool
- Generación de eventos
- Decisión de si termina la ejecución
"""

from dataclasses import dataclass, field
from typing import Any, Optional, AsyncGenerator
from abc import ABC, abstractmethod

from ....models import StreamEvent


@dataclass
class ToolResult:
    """
    Resultado de ejecutar una tool.
    """
    success: bool
    data: dict = field(default_factory=dict)
    
    # Control de flujo
    is_terminal: bool = False  # Si True, termina la ejecución del agente
    final_answer: Optional[str] = None  # Respuesta final si is_terminal
    
    # Eventos a emitir
    events: list[StreamEvent] = field(default_factory=list)
    brain_events: list[str] = field(default_factory=list)  # Brain Event markers
    
    # Para mensajes al LLM
    message_content: str = ""  # Contenido para añadir a messages


class ToolHandler(ABC):
    """
    Clase base para handlers de tools.
    
    Subclases deben implementar:
    - prepare_args(): Preparar argumentos antes de ejecutar
    - process_result(): Procesar resultado después de ejecutar
    """
    
    # Configuración de la tool
    tool_name: str = ""
    display_name: str = ""
    is_terminal: bool = False  # Si True, termina ejecución tras éxito
    
    def __init__(
        self,
        execution_id: str,
        iteration: int,
        emit_brain_events: bool = False,
        llm_config: Optional[dict] = None
    ):
        """
        Args:
            execution_id: ID de la ejecución actual
            iteration: Número de iteración actual
            emit_brain_events: Si True, emite Brain Events
            llm_config: Configuración LLM (url, model, provider, api_key)
        """
        self.execution_id = execution_id
        self.iteration = iteration
        self.emit_brain_events = emit_brain_events
        self.llm_config = llm_config or {}
    
    def prepare_args(self, args: dict) -> dict:
        """
        Prepara argumentos antes de ejecutar.
        Inyecta configuraciones necesarias (LLM config, etc.)
        
        Args:
            args: Argumentos originales de la tool call
            
        Returns:
            Argumentos preparados
        """
        return args.copy()
    
    @abstractmethod
    async def process_result(self, result: dict, args: dict) -> ToolResult:
        """
        Procesa el resultado de la tool.
        
        Args:
            result: Resultado de tool_registry.execute()
            args: Argumentos usados
            
        Returns:
            ToolResult con datos procesados y eventos
        """
        pass
    
    def create_node_start_event(self, args: dict) -> StreamEvent:
        """Crea evento de inicio de nodo."""
        return StreamEvent(
            event_type="node_start",
            execution_id=self.execution_id,
            node_id=f"tool_{self.tool_name}_{self.iteration}",
            node_name=self.display_name,
            data={"tool": self.tool_name, "arguments": args}
        )
    
    def create_node_end_event(self, result: ToolResult, preview: str = "", conversation: str = "") -> StreamEvent:
        """Crea evento de fin de nodo."""
        data = {
            "tool": self.tool_name,
            "success": result.success,
            "result_preview": preview[:200] if preview else "",
            "done": result.is_terminal
        }
        if conversation:
            data["conversation"] = conversation
        return StreamEvent(
            event_type="node_end",
            execution_id=self.execution_id,
            node_id=f"tool_{self.tool_name}_{self.iteration}",
            data=data
        )
    
    def create_token_event(self, content: str, node_id: str = "") -> StreamEvent:
        """Crea evento de token (contenido al stream)."""
        return StreamEvent(
            event_type="token",
            execution_id=self.execution_id,
            node_id=node_id,
            content=content
        )


class DefaultHandler(ToolHandler):
    """
    Handler por defecto para tools sin handler específico.
    """
    
    def __init__(self, tool_name: str, **kwargs):
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.display_name = self._get_display_name(tool_name)
    
    def _get_display_name(self, tool_name: str) -> str:
        """Obtiene nombre amigable para la GUI."""
        names = {
            "read_file": "📖 Leyendo archivo",
            "write_file": "✍️ Escribiendo archivo",
            "edit_file": "✏️ Editando archivo",
            "list_directory": "📁 Listando directorio",
            "search_files": "🔎 Buscando en archivos",
            "shell": "💻 Ejecutando comando",
            "python": "🐍 Ejecutando Python",
            "javascript": "📜 Ejecutando JavaScript",
            "web_search": "🌐 Buscando en web",
            "web_fetch": "📥 Obteniendo URL",
            "calculate": "🔢 Calculando",
        }
        return names.get(tool_name, f"🔧 {tool_name}")
    
    async def process_result(self, result: Any, args: dict) -> ToolResult:
        """Procesamiento por defecto (acepta dict, list, o cualquier tipo)."""
        if isinstance(result, dict):
            return ToolResult(
                success=result.get("success", True),
                data=result,
                message_content=str(result)[:16000],
            )
        return ToolResult(
            success=True,
            data={"raw": result},
            message_content=str(result)[:16000],
        )
