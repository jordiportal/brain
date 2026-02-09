"""
StreamEmitter - Emisor de eventos de streaming.

Centraliza la creación de StreamEvents para mantener consistencia
y reducir duplicación en el código del executor.
"""

from typing import Any, Optional
from ....models import StreamEvent


class StreamEmitter:
    """
    Emisor centralizado de StreamEvents.
    
    Proporciona métodos helper para crear eventos comunes
    manteniendo consistencia en IDs y formatos.
    """
    
    def __init__(self, execution_id: str, chain_id: str = "adaptive"):
        """
        Args:
            execution_id: ID único de la ejecución
            chain_id: ID de la cadena
        """
        self.execution_id = execution_id
        self.chain_id = chain_id
    
    # ========== Eventos de Ciclo de Vida ==========
    
    def chain_start(self, chain_name: str, input_data: dict) -> StreamEvent:
        """Evento de inicio de cadena."""
        return StreamEvent(
            event_type="start",
            execution_id=self.execution_id,
            data={
                "chain_id": self.chain_id,
                "chain_name": chain_name,
                "input": input_data
            }
        )
    
    def chain_end(self, output: dict) -> StreamEvent:
        """Evento de fin de cadena."""
        return StreamEvent(
            event_type="end",
            execution_id=self.execution_id,
            data={"output": output}
        )
    
    # ========== Eventos de Nodos ==========
    
    def node_start(
        self,
        node_id: str,
        node_name: str,
        data: Optional[dict] = None
    ) -> StreamEvent:
        """Evento de inicio de nodo."""
        return StreamEvent(
            event_type="node_start",
            execution_id=self.execution_id,
            node_id=node_id,
            node_name=node_name,
            data=data or {}
        )
    
    def node_end(
        self,
        node_id: str,
        data: Optional[dict] = None
    ) -> StreamEvent:
        """Evento de fin de nodo."""
        return StreamEvent(
            event_type="node_end",
            execution_id=self.execution_id,
            node_id=node_id,
            data=data or {}
        )
    
    # ========== Eventos de Iteración ==========
    
    def iteration_start(self, iteration: int, max_iterations: int) -> StreamEvent:
        """Evento de inicio de iteración."""
        return StreamEvent(
            event_type="node_start",
            execution_id=self.execution_id,
            node_id=f"iteration_{iteration}",
            node_name=f"Iteration {iteration}/{max_iterations}",
            data={"iteration": iteration}
        )
    
    def iteration_end(self, iteration: int, tools_used: int = 0) -> StreamEvent:
        """Evento de fin de iteración."""
        return StreamEvent(
            event_type="node_end",
            execution_id=self.execution_id,
            node_id=f"iteration_{iteration}",
            data={"tools_used": tools_used}
        )
    
    # ========== Eventos de Tools ==========
    
    def tool_start(
        self,
        tool_name: str,
        display_name: str,
        iteration: int,
        args: dict
    ) -> StreamEvent:
        """Evento de inicio de tool."""
        return StreamEvent(
            event_type="node_start",
            execution_id=self.execution_id,
            node_id=f"tool_{tool_name}_{iteration}",
            node_name=display_name,
            data={"tool": tool_name, "arguments": args}
        )
    
    def tool_end(
        self,
        tool_name: str,
        iteration: int,
        success: bool = True,
        preview: str = "",
        thinking: Optional[str] = None,
        done: bool = False,
        html: Optional[str] = None,
        conversation: Optional[str] = None
    ) -> StreamEvent:
        """Evento de fin de tool."""
        data = {
            "tool": tool_name,
            "success": success,
            "result_preview": preview[:200] if preview else "",
            "done": done
        }
        if thinking:
            data["thinking"] = thinking
        if html:
            data["html"] = html
        if conversation:
            data["conversation"] = conversation  # Contenido completo de la conversación
        
        return StreamEvent(
            event_type="node_end",
            execution_id=self.execution_id,
            node_id=f"tool_{tool_name}_{iteration}",
            data=data
        )
    
    # ========== Eventos de Contenido ==========
    
    def token(self, content: str, node_id: str = "") -> StreamEvent:
        """Evento de token (contenido al stream)."""
        return StreamEvent(
            event_type="token",
            execution_id=self.execution_id,
            node_id=node_id,
            content=content
        )
    
    def image(
        self,
        node_id: str,
        url: Optional[str] = None,
        base64_data: Optional[str] = None,
        mime_type: str = "image/png",
        alt_text: str = "Generated image",
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> StreamEvent:
        """Evento de imagen."""
        data = {"alt_text": alt_text}
        
        if url:
            data["image_url"] = url
        elif base64_data:
            data["image_data"] = base64_data
            data["mime_type"] = mime_type
        
        if provider:
            data["provider"] = provider
        if model:
            data["model"] = model
        
        return StreamEvent(
            event_type="image",
            execution_id=self.execution_id,
            node_id=node_id,
            data=data
        )
    
    def video(
        self,
        node_id: str,
        url: Optional[str] = None,
        base64_data: Optional[str] = None,
        mime_type: str = "video/mp4",
        duration_seconds: Optional[int] = None,
        resolution: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None
    ) -> StreamEvent:
        """Evento de vídeo."""
        data: Dict[str, Any] = {}
        
        if url:
            data["video_url"] = url
        elif base64_data:
            data["video_data"] = base64_data
            data["mime_type"] = mime_type
        
        if duration_seconds:
            data["duration_seconds"] = duration_seconds
        if resolution:
            data["resolution"] = resolution
        if provider:
            data["provider"] = provider
        if model:
            data["model"] = model
        
        return StreamEvent(
            event_type="video",
            execution_id=self.execution_id,
            node_id=node_id,
            data=data
        )
    
    # ========== Eventos de Error ==========
    
    def error(self, error_message: str, node_id: str = "") -> StreamEvent:
        """Evento de error."""
        return StreamEvent(
            event_type="error",
            execution_id=self.execution_id,
            node_id=node_id,
            content=f"Error: {error_message}"
        )
    
    # ========== Eventos de Límite de Iteraciones ==========
    
    def iteration_limit(
        self,
        iterations_used: int,
        max_iterations: int,
        tools_used: list[str],
        message: str
    ) -> StreamEvent:
        """Evento de límite de iteraciones alcanzado."""
        return StreamEvent(
            event_type="iteration_limit",
            execution_id=self.execution_id,
            node_id="limit_reached",
            node_name="Límite de iteraciones alcanzado",
            content=message,
            data={
                "iterations_used": iterations_used,
                "max_iterations": max_iterations,
                "tools_used": tools_used,
                "can_continue": True
            }
        )
    
    # ========== Eventos de Respuesta Completa ==========
    
    def response_complete(
        self,
        content: str,
        complexity: str,
        iterations: int,
        tools_used: list[str],
        iteration_limit_reached: bool = False,
        can_continue: bool = False
    ) -> StreamEvent:
        """Evento de respuesta completa."""
        data = {
            "complexity": complexity,
            "iterations": iterations,
            "tools_used": tools_used
        }
        
        if iteration_limit_reached:
            data["iteration_limit_reached"] = True
            data["can_continue"] = can_continue
        
        return StreamEvent(
            event_type="response_complete",
            execution_id=self.execution_id,
            node_id="adaptive_agent",
            content=content,
            data=data
        )
