"""
Brain Events - Helpers para emitir eventos compatibles con Open WebUI

Los Brain Events son markers HTML embebidos en el stream de texto:
<!--BRAIN_EVENT:{"type":"thinking","content":"..."}-->

Tipos de eventos:
- thinking: Razonamiento del agente
- action: Acciones en progreso (search, slides, code_exec, etc.)
- sources: Fuentes consultadas
- artifact: Contenido generado (slides, docs, etc.)
"""

import json
import base64
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .models import StreamEvent


@dataclass
class BrainEventConfig:
    """Configuración para emisión de Brain Events."""
    enabled: bool = False
    include_thinking: bool = True
    include_actions: bool = True
    include_sources: bool = True
    include_artifacts: bool = True


# ============================================
# Funciones para crear Brain Event markers
# ============================================

def create_brain_event_marker(event_type: str, **kwargs) -> str:
    """
    Crea un marker de Brain Event.
    
    Args:
        event_type: thinking, action, sources, artifact
        **kwargs: Campos adicionales del evento
    
    Returns:
        String con el marker HTML: <!--BRAIN_EVENT:{json}-->
    """
    event = {"type": event_type, **kwargs}
    # Asegurar que el JSON esté en una línea
    json_str = json.dumps(event, ensure_ascii=False, separators=(',', ':'))
    return f"\n<!--BRAIN_EVENT:{json_str}-->\n"


def create_thinking_event(
    content: str,
    status: str = "progress"
) -> str:
    """
    Crea evento de thinking/razonamiento.
    
    Args:
        content: Texto del razonamiento (soporta markdown)
        status: start, progress, complete, error
    """
    return create_brain_event_marker("thinking", content=content, status=status)


def create_action_event(
    action_type: str,
    title: str,
    status: str,
    description: Optional[str] = None,
    results_count: Optional[int] = None,
    delegation_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    agent_icon: Optional[str] = None,
    duration_ms: Optional[int] = None,
    results_summary: Optional[str] = None,
) -> str:
    """
    Crea evento de acción.
    
    Args:
        action_type: search, python, shell, javascript, web_search, web_fetch,
                     file_read, file_write, slides, image, data, files, web,
                     delegate, summarizing, planning, code_exec (legacy)
        title: Descripción de la acción
        status: running, completed, error
        description: Detalle adicional
        results_count: Número de resultados
        delegation_id: ID para agrupar eventos de una delegación
        agent_name: Nombre amigable del subagente (para delegate)
        agent_icon: Ícono del subagente
        duration_ms: Duración en ms (para completed)
        results_summary: Resumen de resultados (para completed)
    """
    event_data = {
        "action_type": action_type,
        "title": title,
        "status": status
    }
    if description:
        event_data["description"] = description
    if results_count is not None:
        event_data["results_count"] = results_count
    if delegation_id:
        event_data["delegation_id"] = delegation_id
    if agent_name:
        event_data["agent_name"] = agent_name
    if agent_icon:
        event_data["agent_icon"] = agent_icon
    if duration_ms is not None:
        event_data["duration_ms"] = duration_ms
    if results_summary:
        event_data["results_summary"] = results_summary
    
    return create_brain_event_marker("action", **event_data)


def create_sources_event(sources: List[Dict[str, str]]) -> str:
    """
    Crea evento de fuentes consultadas.
    
    Args:
        sources: Lista de fuentes con url, title, snippet, favicon, date
    """
    # Formatear fuentes
    formatted = []
    for s in sources[:10]:  # Máximo 10 fuentes
        formatted.append({
            "url": s.get("url", ""),
            "title": s.get("title", "Fuente"),
            "snippet": (s.get("snippet", "") or "")[:200],
            "favicon": s.get("favicon", "🌐"),
            "date": s.get("date")
        })
    
    return create_brain_event_marker("sources", sources=formatted)


def create_artifact_event(
    artifact_type: str,
    title: str,
    content: str,
    format: str = "html"
) -> str:
    """
    Crea evento de artifact con contenido en base64.
    
    Args:
        artifact_type: slides, document, code, etc.
        title: Título del artifact
        content: Contenido (se codifica en base64)
        format: html, markdown, text
    """
    content_b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
    return create_brain_event_marker(
        "artifact",
        artifact_type=artifact_type,
        title=title,
        content_base64=content_b64,
        format=format
    )


def create_artifact_url_event(
    artifact_type: str,
    title: str,
    url: str,
    artifact_id: Optional[str] = None,
    mime_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Crea evento de artifact con URL (sin contenido inline).
    OpenWebUI cargará el contenido via proxy desde la URL.
    """
    kwargs: Dict[str, Any] = {
        "artifact_type": artifact_type,
        "title": title,
        "url": url,
    }
    if artifact_id:
        kwargs["artifact_id"] = artifact_id
    if mime_type:
        kwargs["mime_type"] = mime_type
    if metadata:
        kwargs["metadata"] = metadata
    return create_brain_event_marker("artifact", **kwargs)


# ============================================
# Funciones para crear StreamEvents con Brain Events
# ============================================

def brain_event_stream(
    execution_id: str,
    brain_event_marker: str,
    node_id: str = "brain_event"
) -> StreamEvent:
    """
    Crea un StreamEvent que contiene un Brain Event marker.
    
    Args:
        execution_id: ID de la ejecución
        brain_event_marker: El marker creado con create_*_event()
        node_id: ID del nodo
    
    Returns:
        StreamEvent con el marker como content
    """
    return StreamEvent(
        event_type="token",
        execution_id=execution_id,
        node_id=node_id,
        content=brain_event_marker
    )


def emit_thinking(
    execution_id: str,
    content: str,
    status: str = "progress"
) -> StreamEvent:
    """Helper para emitir thinking event."""
    return brain_event_stream(
        execution_id=execution_id,
        brain_event_marker=create_thinking_event(content, status),
        node_id="thinking"
    )


def emit_action_start(
    execution_id: str,
    action_type: str,
    title: str,
    description: Optional[str] = None
) -> StreamEvent:
    """Helper para emitir action start event."""
    return brain_event_stream(
        execution_id=execution_id,
        brain_event_marker=create_action_event(
            action_type=action_type,
            title=title,
            status="running",
            description=description
        ),
        node_id=f"action_{action_type}"
    )


def emit_action_complete(
    execution_id: str,
    action_type: str,
    title: str,
    results_count: Optional[int] = None
) -> StreamEvent:
    """Helper para emitir action complete event."""
    return brain_event_stream(
        execution_id=execution_id,
        brain_event_marker=create_action_event(
            action_type=action_type,
            title=title,
            status="completed",
            results_count=results_count
        ),
        node_id=f"action_{action_type}"
    )


def emit_sources(
    execution_id: str,
    sources: List[Dict[str, str]]
) -> StreamEvent:
    """Helper para emitir sources event."""
    return brain_event_stream(
        execution_id=execution_id,
        brain_event_marker=create_sources_event(sources),
        node_id="sources"
    )


def emit_artifact(
    execution_id: str,
    artifact_type: str,
    title: str,
    content: str,
    format: str = "html"
) -> StreamEvent:
    """Helper para emitir artifact event."""
    return brain_event_stream(
        execution_id=execution_id,
        brain_event_marker=create_artifact_event(
            artifact_type=artifact_type,
            title=title,
            content=content,
            format=format
        ),
        node_id=f"artifact_{artifact_type}"
    )


def emit_artifact_url(
    execution_id: str,
    artifact_type: str,
    title: str,
    url: str,
    artifact_id: Optional[str] = None,
    mime_type: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> StreamEvent:
    """Helper para emitir artifact URL event."""
    return brain_event_stream(
        execution_id=execution_id,
        brain_event_marker=create_artifact_url_event(
            artifact_type=artifact_type,
            title=title,
            url=url,
            artifact_id=artifact_id,
            mime_type=mime_type,
            metadata=metadata,
        ),
        node_id=f"artifact_{artifact_type}"
    )


# ============================================
# Mapeo de tools a action_types
# ============================================

TOOL_TO_ACTION_TYPE = {
    "web_search": "web_search",
    "web_fetch": "web_fetch",
    "read_file": "file_read",
    "write_file": "file_write",
    "python": "python",
    "shell": "shell",
    "javascript": "javascript",
    "generate_image": "image",
    "delegate": "delegate",
}

AGENT_TO_ACTION_TYPE = {
    "designer_agent": "image",
    "researcher_agent": "web_search",
    "communication_agent": "data",
    "sap_analyst": "data_analysis",
}

AGENT_FRIENDLY_NAMES = {
    "designer_agent": ("Diseñador", "image"),
    "researcher_agent": ("Investigador", "search"),
    "communication_agent": ("Comunicador", "data"),
    "sap_analyst": ("Analista SAP", "data"),
}


def get_agent_friendly_name(agent_id: str) -> tuple[str, str]:
    """Returns (display_name, icon_key) for a subagent."""
    if agent_id in AGENT_FRIENDLY_NAMES:
        return AGENT_FRIENDLY_NAMES[agent_id]
    name = agent_id.replace("_agent", "").replace("_", " ").title()
    return (name, "data")


def get_action_type_for_tool(tool_name: str, agent: Optional[str] = None, task: Optional[str] = None) -> str:
    """
    Obtiene el action_type para una tool.
    """
    if tool_name == "delegate":
        return "delegate"
    
    return TOOL_TO_ACTION_TYPE.get(tool_name, "data")


def get_action_title_for_tool(tool_name: str, args: Dict[str, Any]) -> str:
    """
    Genera un título descriptivo para una acción.
    """
    def _get_reasoning_preview(a, field: str) -> str:
        content = a.get(field, a.get("thought", ""))[:100]
        if content:
            first_line = content.split('\n')[0][:80]
            return first_line if first_line else content[:80]
        return ""
    
    titles = {
        "web_search": lambda a: f"Buscando: {a.get('query', '')[:50]}",
        "web_fetch": lambda a: f"Obteniendo: {a.get('url', '')[:50]}",
        "read_file": lambda a: f"Leyendo: {a.get('path', '').split('/')[-1]}",
        "write_file": lambda a: f"Escribiendo: {a.get('path', '').split('/')[-1]}",
        "python": lambda a: "Ejecutando código Python",
        "shell": lambda a: f"Ejecutando: {a.get('command', '')[:30]}",
        "javascript": lambda a: "Ejecutando JavaScript",
        "generate_image": lambda a: f"Generando imagen: {a.get('prompt', '')[:40]}",
        "delegate": lambda a: a.get('task', '')[:60] or f"Delegando a {a.get('agent', 'subagente')}",
        "think": lambda a: f"💭 {_get_reasoning_preview(a, 'thought')}" if _get_reasoning_preview(a, 'thought') else "Analizando...",
        "plan": lambda a: f"📋 {_get_reasoning_preview(a, 'plan')}" if _get_reasoning_preview(a, 'plan') else "Planificando...",
        "reflect": lambda a: f"🔍 {_get_reasoning_preview(a, 'reflection')}" if _get_reasoning_preview(a, 'reflection') else "Reflexionando...",
    }
    
    title_fn = titles.get(tool_name, lambda a: f"Ejecutando {tool_name}")
    return title_fn(args)
