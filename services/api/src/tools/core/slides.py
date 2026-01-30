"""
Slides Generation Tool - Generación de presentaciones con streaming real

Esta tool genera presentaciones HTML con streaming progresivo de Brain Events.
A diferencia de delegate(), esta tool emite eventos en tiempo real.

Uso desde el adaptive_agent:
    generate_slides(outline='{"title":"...", "slides":[...]}', context="...")
"""

import json
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator, Callable

import structlog

from src.engine.brain_events import (
    create_thinking_event,
    create_action_event,
    create_sources_event,
    create_artifact_event
)

logger = structlog.get_logger()


# Callback type para emitir eventos durante la generación
EventCallback = Callable[[str], None]


async def generate_slides(
    outline: str,
    context: Optional[str] = None,
    _event_callback: Optional[EventCallback] = None,
    _llm_url: Optional[str] = None,
    _model: Optional[str] = None,
    _provider_type: str = "ollama",
    _api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Genera una presentación HTML con streaming de Brain Events.
    
    Esta tool está diseñada para emitir eventos progresivos durante
    la generación, proporcionando feedback en tiempo real al usuario.
    
    Args:
        outline: JSON string con la estructura de la presentación:
                 {"title": "...", "slides": [{"title": "...", "type": "...", ...}]}
        context: Información adicional recopilada (fuentes, datos, etc.)
        _event_callback: Callback para emitir eventos (inyectado por el sistema)
        _llm_url: URL del LLM (inyectada)
        _model: Modelo (inyectado)
        _provider_type: Proveedor (inyectado)
        _api_key: API key (inyectada)
    
    Returns:
        Dict con:
        - success: bool
        - html: HTML completo de la presentación
        - title: Título de la presentación
        - slides_count: Número de slides
        - events_emitted: Lista de eventos emitidos
    """
    logger.info("📊 generate_slides called", outline_length=len(outline))
    
    events_emitted = []
    
    def emit(event: str):
        """Emite un evento y lo registra."""
        events_emitted.append(event)
        if _event_callback:
            _event_callback(event)
    
    try:
        # 1. Thinking: Procesando
        emit(create_thinking_event(
            "Procesando solicitud de presentación...",
            status="start"
        ))
        
        # 2. Parsear outline
        try:
            data = json.loads(outline)
            title = data.get("title", "Presentación")
            slides_data = data.get("slides", [])
        except json.JSONDecodeError as e:
            emit(create_thinking_event(
                f"Error parseando outline: {e}",
                status="error"
            ))
            return {
                "success": False,
                "error": f"Invalid JSON outline: {e}",
                "events_emitted": events_emitted
            }
        
        if not slides_data:
            return {
                "success": False,
                "error": "No slides in outline",
                "events_emitted": events_emitted
            }
        
        emit(create_thinking_event(
            f"Outline recibido: {title}\n- {len(slides_data)} slides a generar",
            status="complete"
        ))
        
        # 3. Action: Generando slides
        emit(create_action_event(
            action_type="slides",
            title=f"Generando {len(slides_data)} slides",
            status="running"
        ))
        
        # 4. Generar slides progresivamente
        html = _get_slides_css()
        
        for i, slide in enumerate(slides_data, 1):
            # Pequeña pausa para UX (permite que los eventos se envíen)
            await asyncio.sleep(0.1)
            
            # Generar slide
            slide_html = _generate_slide_html(slide, i, len(slides_data))
            html += slide_html
            
            # Emitir artifact progresivo
            emit(create_artifact_event(
                artifact_type="slides",
                title=title,
                content=html,
                format="html"
            ))
            
            logger.debug(f"Slide {i}/{len(slides_data)} generated")
        
        # 5. Completar
        emit(create_action_event(
            action_type="slides",
            title=f"Generando {len(slides_data)} slides",
            status="completed"
        ))
        
        slides_count = html.count('class="slide"')
        
        logger.info(
            "✅ generate_slides completed",
            title=title,
            slides_count=slides_count,
            events=len(events_emitted)
        )
        
        return {
            "success": True,
            "html": html,
            "title": title,
            "slides_count": slides_count,
            "events_emitted": events_emitted,
            "message": f"Presentación '{title}' generada con {slides_count} slides"
        }
        
    except Exception as e:
        logger.error(f"generate_slides error: {e}", exc_info=True)
        emit(create_action_event(
            action_type="slides",
            title="Error generando slides",
            status="error",
            description=str(e)
        ))
        return {
            "success": False,
            "error": str(e),
            "events_emitted": events_emitted
        }


def _get_slides_css() -> str:
    """Retorna el CSS para las slides."""
    return """
<style>
.slide {
  padding: 32px;
  margin-bottom: 16px;
  border-radius: 12px;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  color: #fff;
  min-height: 400px;
}
.slide h1 {
  font-size: 2.2rem;
  margin-bottom: 16px;
  color: #e94560;
}
.slide h2 {
  font-size: 1.6rem;
  margin-bottom: 12px;
  color: #0f3460;
  background: linear-gradient(90deg, #e94560, #f39c12);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.slide p {
  font-size: 1.1rem;
  line-height: 1.6;
  margin-bottom: 12px;
}
.slide ul, .slide ol {
  margin-left: 24px;
  margin-bottom: 16px;
}
.slide li {
  margin-bottom: 8px;
  line-height: 1.5;
}
.badge {
  display: inline-block;
  padding: 4px 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
  border-radius: 20px;
  background: rgba(233, 69, 96, 0.2);
  color: #e94560;
  margin-bottom: 12px;
}
.highlight {
  color: #f39c12;
  font-weight: 600;
}
.stats {
  display: flex;
  gap: 32px;
  margin: 24px 0;
}
.stat-value {
  font-size: 2.5rem;
  font-weight: 700;
  color: #e94560;
}
.stat-label {
  font-size: 0.9rem;
  color: #888;
}
.grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin: 20px 0;
}
.card {
  background: rgba(255,255,255,0.05);
  padding: 20px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.1);
}
.card-title {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 8px;
  color: #e94560;
}
.card-desc {
  font-size: 0.95rem;
  color: #ccc;
}
.quote {
  border-left: 4px solid #e94560;
  padding-left: 20px;
  font-style: italic;
  margin: 20px 0;
  color: #ddd;
}
</style>
"""


def _generate_slide_html(slide: Dict[str, Any], num: int, total: int) -> str:
    """Genera el HTML para una slide."""
    slide_type = slide.get("type", "content")
    title = slide.get("title", f"Slide {num}")
    content = slide.get("content", "")
    badge = slide.get("badge", "")
    bullets = slide.get("bullets", [])
    stats = slide.get("stats", [])
    items = slide.get("items", [])
    quote = slide.get("quote", "")
    author = slide.get("author", "")
    
    html_parts = ['<div class="slide">']
    
    # Badge
    if badge:
        html_parts.append(f'  <span class="badge">{badge}</span>')
    
    # Título
    if slide_type == "title":
        html_parts.append(f'  <h1>{title}</h1>')
    else:
        html_parts.append(f'  <h2>{title}</h2>')
    
    # Contenido según tipo
    if content:
        html_parts.append(f'  <p>{content}</p>')
    
    if bullets:
        html_parts.append('  <ul>')
        for bullet in bullets:
            html_parts.append(f'    <li>{bullet}</li>')
        html_parts.append('  </ul>')
    
    if stats:
        html_parts.append('  <div class="stats">')
        for stat in stats:
            html_parts.append(f'''    <div>
      <div class="stat-value">{stat.get("value", "")}</div>
      <div class="stat-label">{stat.get("label", "")}</div>
    </div>''')
        html_parts.append('  </div>')
    
    if items:
        html_parts.append('  <div class="grid">')
        for item in items:
            html_parts.append(f'''    <div class="card">
      <div class="card-title">{item.get("title", "")}</div>
      <div class="card-desc">{item.get("description", "")}</div>
    </div>''')
        html_parts.append('  </div>')
    
    if quote:
        html_parts.append(f'  <div class="quote">"{quote}"</div>')
        if author:
            html_parts.append(f'  <p>— {author}</p>')
    
    html_parts.append('</div>\n')
    
    return '\n'.join(html_parts)


# ============================================
# Tool Definition
# ============================================

GENERATE_SLIDES_TOOL = {
    "id": "generate_slides",
    "name": "generate_slides",
    "description": """Genera una presentación HTML profesional con streaming progresivo.

Usa esta tool para crear presentaciones con slides visualmente atractivas.
PRIMERO debes crear un outline JSON estructurado, luego llamar a esta tool.

Formato del outline:
- title: Título de la presentación
- slides: Array de objetos slide

Cada slide puede tener:
- title: Título de la slide
- type: title, content, bullets, stats, comparison, quote
- content: Texto de contenido (opcional)
- badge: Etiqueta como "INTRO", "DATOS", "RESUMEN" (opcional)
- bullets: Array de puntos (para type bullets)
- stats: Array de estadísticas con value y label (para type stats)
- items: Array de items con title y description (para type comparison)
- quote: Texto de cita (para type quote)
- author: Autor de la cita (opcional)

Ejemplo de uso:
generate_slides(outline='{"title":"Mi Presentación","slides":[{"title":"Intro","type":"title","badge":"INICIO"},{"title":"Puntos clave","type":"bullets","bullets":["Punto 1","Punto 2"]}]}')""",
    "parameters": {
        "type": "object",
        "properties": {
            "outline": {
                "type": "string",
                "description": "JSON string con la estructura de la presentación (title y slides array)"
            },
            "context": {
                "type": "string",
                "description": "Información adicional recopilada (fuentes, datos) para incluir en las slides"
            }
        },
        "required": ["outline"]
    },
    "handler": generate_slides
}
