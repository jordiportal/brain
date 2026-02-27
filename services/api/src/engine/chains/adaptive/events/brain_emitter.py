"""
BrainEmitter - Emisor de Brain Events para Open WebUI.

Genera markers HTML en formato <!--BRAIN_EVENT:{json}-->
que Open WebUI interpreta para mostrar UI enriquecida.
"""

from typing import Optional, Any
from ....models import StreamEvent
from ....brain_events import (
    create_thinking_event,
    create_action_event,
    create_sources_event,
    create_artifact_event,
    create_artifact_url_event,
    get_action_type_for_tool,
    get_action_title_for_tool
)


class BrainEmitter:
    """
    Emisor de Brain Events para integración con Open WebUI.
    
    Los Brain Events son markers HTML embebidos en el stream de texto
    que Open WebUI parsea para mostrar UI especial (thinking, actions,
    sources, artifacts).
    """
    
    def __init__(self, execution_id: str, enabled: bool = False):
        """
        Args:
            execution_id: ID de la ejecución
            enabled: Si False, todos los métodos retornan None
        """
        self.execution_id = execution_id
        self.enabled = enabled
    
    def _wrap_in_stream_event(
        self,
        content: str,
        node_id: str = "brain_event"
    ) -> Optional[StreamEvent]:
        """Envuelve un marker en un StreamEvent."""
        if not self.enabled or not content:
            return None
        
        return StreamEvent(
            event_type="token",
            execution_id=self.execution_id,
            node_id=node_id,
            content=content
        )
    
    # ========== Eventos de Thinking ==========
    
    def thinking(
        self,
        content: str,
        status: str = "progress"
    ) -> Optional[StreamEvent]:
        """
        Emite evento de thinking/razonamiento.
        
        Args:
            content: Texto del pensamiento (soporta markdown)
            status: start, progress, complete, error
        """
        marker = create_thinking_event(content, status)
        return self._wrap_in_stream_event(marker, "brain_thinking")
    
    def thinking_start(self, content: str) -> Optional[StreamEvent]:
        """Atajo para thinking con status=start."""
        return self.thinking(content, status="start")
    
    def thinking_complete(self, content: str) -> Optional[StreamEvent]:
        """Atajo para thinking con status=complete."""
        return self.thinking(content, status="complete")
    
    # ========== Eventos de Action ==========
    
    def action(
        self,
        action_type: str,
        title: str,
        status: str,
        description: Optional[str] = None,
        results_count: Optional[int] = None
    ) -> Optional[StreamEvent]:
        """
        Emite evento de acción.
        
        Args:
            action_type: search, read, write, code_exec, slides, image, data, files, web
            title: Descripción de la acción
            status: running, completed, error
            description: Detalle adicional
            results_count: Número de resultados
        """
        marker = create_action_event(
            action_type=action_type,
            title=title,
            status=status,
            description=description,
            results_count=results_count
        )
        return self._wrap_in_stream_event(marker, f"brain_action_{action_type}")
    
    def action_for_tool(
        self,
        tool_name: str,
        args: dict,
        status: str = "running",
        results_count: Optional[int] = None
    ) -> Optional[StreamEvent]:
        """
        Emite evento de action para una tool.
        
        Args:
            tool_name: Nombre de la tool
            args: Argumentos de la tool
            status: running, completed, error
            results_count: Número de resultados (para web_search, etc.)
        """
        action_type = get_action_type_for_tool(
            tool_name,
            agent=args.get("agent") if tool_name == "delegate" else None,
            task=args.get("task") if tool_name == "delegate" else None,
        )
        title = get_action_title_for_tool(tool_name, args)
        
        return self.action(
            action_type=action_type,
            title=title,
            status=status,
            results_count=results_count
        )
    
    def action_start(
        self,
        tool_name: str,
        args: dict
    ) -> Optional[StreamEvent]:
        """Atajo para action_for_tool con status=running."""
        return self.action_for_tool(tool_name, args, status="running")
    
    def action_complete(
        self,
        tool_name: str,
        args: dict,
        results_count: Optional[int] = None
    ) -> Optional[StreamEvent]:
        """Atajo para action_for_tool con status=completed."""
        return self.action_for_tool(
            tool_name, args,
            status="completed",
            results_count=results_count
        )
    
    # ========== Eventos de Sources ==========
    
    def sources(self, sources_list: list[dict]) -> Optional[StreamEvent]:
        """
        Emite evento de fuentes consultadas.
        
        Args:
            sources_list: Lista de fuentes con url, title, snippet, favicon, date
        """
        if not sources_list:
            return None
        
        marker = create_sources_event(sources_list)
        return self._wrap_in_stream_event(marker, "brain_sources")
    
    def sources_from_web_search(self, result: dict) -> Optional[StreamEvent]:
        """
        Extrae y emite sources de un resultado de web_search.
        
        Args:
            result: Resultado de web_search con 'results' o 'sources'
        """
        sources = result.get("results") or result.get("sources") or []
        return self.sources(sources)
    
    # ========== Eventos de Artifact ==========
    
    def artifact(
        self,
        artifact_type: str,
        title: str,
        content: str,
        format: str = "html"
    ) -> Optional[StreamEvent]:
        """
        Emite evento de artifact con contenido en base64.
        
        Args:
            artifact_type: slides, document, code, etc.
            title: Título del artifact
            content: Contenido (se codifica en base64)
            format: html, markdown, text
        """
        marker = create_artifact_event(
            artifact_type=artifact_type,
            title=title,
            content=content,
            format=format
        )
        return self._wrap_in_stream_event(marker, f"brain_artifact_{artifact_type}")
    
    def artifact_url(
        self,
        artifact_type: str,
        title: str,
        url: str,
        artifact_id: Optional[str] = None,
        mime_type: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[StreamEvent]:
        """
        Emite evento de artifact con URL (sin contenido inline).
        OpenWebUI descargará el contenido via proxy.
        """
        marker = create_artifact_url_event(
            artifact_type=artifact_type,
            title=title,
            url=url,
            artifact_id=artifact_id,
            mime_type=mime_type,
            metadata=metadata,
        )
        return self._wrap_in_stream_event(marker, f"brain_artifact_{artifact_type}")

    # ========== Helpers ==========
    
    def get_results_count(self, tool_name: str, result: dict) -> Optional[int]:
        """
        Extrae el número de resultados de un resultado de tool.
        """
        if tool_name == "web_search" and isinstance(result, dict):
            if "results" in result:
                return len(result.get("results", []))
            elif "sources" in result:
                return len(result.get("sources", []))
        return None
