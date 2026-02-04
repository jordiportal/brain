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
    results_count: Optional[int] = None
) -> str:
    """
    Crea evento de acción.
    
    Args:
        action_type: search, read, write, code_exec, slides, image, data, files, web
        title: Descripción de la acción
        status: running, completed, error
        description: Detalle adicional
        results_count: Número de resultados
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


# ============================================
# Mapeo de tools a action_types
# ============================================

TOOL_TO_ACTION_TYPE = {
    "web_search": "search",
    "web_fetch": "web",
    "read_file": "read",
    "write_file": "write",
    "python": "code_exec",
    "shell": "code_exec",
    "javascript": "code_exec",
    "generate_image": "image",
    "delegate": "data",  # Generic, se sobrescribe según el subagente
}

def get_action_type_for_tool(tool_name: str, agent: Optional[str] = None) -> str:
    """
    Obtiene el action_type para una tool.
    
    Args:
        tool_name: Nombre de la tool
        agent: Si es delegate, el subagente destino
    
    Returns:
        action_type para el Brain Event
    """
    if tool_name == "delegate" and agent:
        if agent == "designer_agent":
            return "slides"  # Imágenes y presentaciones
        else:
            return "data"
    
    return TOOL_TO_ACTION_TYPE.get(tool_name, "data")


def get_action_title_for_tool(tool_name: str, args: Dict[str, Any]) -> str:
    """
    Genera un título descriptivo para una acción.
    
    Args:
        tool_name: Nombre de la tool
        args: Argumentos de la tool
    
    Returns:
        Título descriptivo
    """
    # Para tools de razonamiento, extraer preview del contenido
    def _get_reasoning_preview(a, field: str) -> str:
        content = a.get(field, a.get("thought", ""))[:100]
        if content:
            # Primera línea o primeros 100 chars
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
        "delegate": lambda a: f"Delegando a {a.get('agent', 'subagente')}",
        "think": lambda a: f"💭 {_get_reasoning_preview(a, 'thought')}" if _get_reasoning_preview(a, 'thought') else "Analizando...",
        "plan": lambda a: f"📋 {_get_reasoning_preview(a, 'plan')}" if _get_reasoning_preview(a, 'plan') else "Planificando...",
        "reflect": lambda a: f"🔍 {_get_reasoning_preview(a, 'reflection')}" if _get_reasoning_preview(a, 'reflection') else "Reflexionando...",
    }
    
    title_fn = titles.get(tool_name, lambda a: f"Ejecutando {tool_name}")
    return title_fn(args)
