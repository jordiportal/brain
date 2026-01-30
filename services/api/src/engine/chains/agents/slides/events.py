"""Brain Event helpers para Slides Agent."""

import json
import base64
from typing import Optional, List, Dict


def create_brain_event(event_type: str, **kwargs) -> str:
    """Crea un marker de Brain Event."""
    event = {"type": event_type, **kwargs}
    return f"\n<!--BRAIN_EVENT:{json.dumps(event, ensure_ascii=False)}-->\n"


def thinking_event(content: str, status: str = "progress") -> str:
    """Evento de thinking."""
    return create_brain_event("thinking", content=content, status=status)


def action_event(
    action_type: str,
    title: str,
    status: str,
    results_count: Optional[int] = None
) -> str:
    """Evento de acción."""
    data = {
        "type": "action",
        "action_type": action_type,
        "title": title,
        "status": status
    }
    if results_count is not None:
        data["results_count"] = results_count
    return f"\n<!--BRAIN_EVENT:{json.dumps(data, ensure_ascii=False)}-->\n"


def sources_event(sources: List[Dict[str, str]]) -> str:
    """Evento de fuentes."""
    return create_brain_event("sources", sources=sources)


def artifact_event(html_content: str, title: str) -> str:
    """Evento de artifact (slides) con contenido en base64."""
    content_b64 = base64.b64encode(html_content.encode("utf-8")).decode("ascii")
    return create_brain_event(
        "artifact",
        artifact_type="slides",
        title=title,
        content_base64=content_b64,
        format="html"
    )
