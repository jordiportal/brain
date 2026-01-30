"""
Handler para tools de razonamiento: think, reflect, plan.

Estas tools permiten al agente razonar sobre la tarea actual.
"""

from .base import ToolHandler, ToolResult
from ....models import StreamEvent


class ReasoningHandler(ToolHandler):
    """
    Handler para tools de razonamiento.
    No son terminales - el agente continúa después.
    """
    
    is_terminal = False
    
    # Mapeo de tool -> campo del resultado
    RESULT_FIELDS = {
        "think": "thinking",
        "reflect": "reflection",
        "plan": "plan",
    }
    
    # Display names
    DISPLAY_NAMES = {
        "think": "💭 Pensando",
        "reflect": "🔍 Reflexionando",
        "plan": "📋 Planificando",
    }
    
    def __init__(self, tool_name: str = "think", **kwargs):
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.display_name = self.DISPLAY_NAMES.get(tool_name, "💭 Razonando")
    
    async def process_result(self, result: dict, args: dict) -> ToolResult:
        """
        Procesa el resultado de la tool de razonamiento.
        
        Extrae el contenido del pensamiento y genera Brain Events si aplica.
        """
        events = []
        brain_events = []
        
        # Extraer contenido del pensamiento
        field_name = self.RESULT_FIELDS.get(self.tool_name, "thinking")
        thinking_content = (
            result.get(field_name) or 
            result.get("thinking") or 
            result.get("result") or 
            ""
        )
        
        # Emitir Brain Event de thinking si está activado
        if self.emit_brain_events and thinking_content:
            from ....brain_events import create_thinking_event
            
            brain_marker = create_thinking_event(thinking_content, status="progress")
            events.append(StreamEvent(
                event_type="token",
                execution_id=self.execution_id,
                node_id="brain_thinking",
                content=brain_marker
            ))
            brain_events.append(brain_marker)
        
        return ToolResult(
            success=True,
            data={
                field_name: thinking_content,
                "tool": self.tool_name
            },
            is_terminal=False,
            events=events,
            brain_events=brain_events,
            message_content=thinking_content[:4000] if thinking_content else ""
        )
