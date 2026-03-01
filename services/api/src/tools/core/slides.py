"""
Slides Generation Tool - Generación de presentaciones con streaming real

Esta tool genera presentaciones HTML con streaming progresivo de Brain Events.
Soporta slides de texto, estadísticas, cards, citas y gráficos SVG (bar, pie, line, donut, horizontal-bar).

Uso desde el adaptive_agent:
    generate_slides(outline='{"title":"...", "slides":[...]}', context="...")
"""

import json
import math
import asyncio
from typing import Dict, Any, List, Optional, Callable

import structlog

from src.engine.brain_events import (
    create_thinking_event,
    create_action_event,
    create_sources_event,
    create_artifact_event
)

logger = structlog.get_logger()

EventCallback = Callable[[str], None]

# Palette for charts — vibrant colours that work on dark backgrounds
CHART_COLORS = [
    "#e94560", "#f39c12", "#2ecc71", "#3498db",
    "#9b59b6", "#1abc9c", "#e67e22", "#e74c3c",
    "#00cec9", "#fdcb6e", "#6c5ce7", "#ff7675",
]


# ════════════════════════════════════════════
# SVG Chart Renderers
# ════════════════════════════════════════════

def _chart_color(index: int, custom_colors: List[str] | None = None) -> str:
    palette = custom_colors or CHART_COLORS
    return palette[index % len(palette)]


def _svg_bar_chart(data: List[Dict], colors: List[str] | None = None) -> str:
    if not data:
        return ""
    max_val = max((d.get("value", 0) for d in data), default=1) or 1
    n = len(data)
    svg_w, svg_h = 500, 260
    bar_area_h = 200
    gap = 8
    bar_w = max(20, min(60, (svg_w - gap * (n + 1)) // n))
    total_w = n * bar_w + (n + 1) * gap
    offset_x = (svg_w - total_w) / 2

    bars = []
    for i, d in enumerate(data):
        val = d.get("value", 0)
        label = d.get("label", "")
        h = (val / max_val) * (bar_area_h - 30)
        x = offset_x + gap + i * (bar_w + gap)
        y = bar_area_h - h
        c = _chart_color(i, colors)
        bars.append(
            f'<rect x="{x}" y="{y}" width="{bar_w}" height="{h}" rx="4" fill="{c}" opacity="0.9"/>'
            f'<text x="{x + bar_w/2}" y="{y - 6}" text-anchor="middle" fill="#fff" font-size="11" font-weight="600">{val}</text>'
            f'<text x="{x + bar_w/2}" y="{bar_area_h + 16}" text-anchor="middle" fill="#aaa" font-size="10">{_truncate(label, 10)}</text>'
        )
    return (
        f'<svg viewBox="0 0 {svg_w} {svg_h}" xmlns="http://www.w3.org/2000/svg" class="chart-svg">'
        f'<line x1="0" y1="{bar_area_h}" x2="{svg_w}" y2="{bar_area_h}" stroke="#444" stroke-width="1"/>'
        + "".join(bars)
        + "</svg>"
    )


def _svg_horizontal_bar_chart(data: List[Dict], colors: List[str] | None = None) -> str:
    if not data:
        return ""
    max_val = max((d.get("value", 0) for d in data), default=1) or 1
    n = len(data)
    row_h = 36
    label_w = 100
    svg_w, svg_h = 500, n * row_h + 20
    bar_area_w = svg_w - label_w - 60

    bars = []
    for i, d in enumerate(data):
        val = d.get("value", 0)
        label = d.get("label", "")
        w = (val / max_val) * bar_area_w
        y = 10 + i * row_h
        c = _chart_color(i, colors)
        bars.append(
            f'<text x="{label_w - 8}" y="{y + 20}" text-anchor="end" fill="#ccc" font-size="11">{_truncate(label, 14)}</text>'
            f'<rect x="{label_w}" y="{y + 6}" width="{w}" height="{row_h - 14}" rx="4" fill="{c}" opacity="0.9"/>'
            f'<text x="{label_w + w + 6}" y="{y + 20}" fill="#fff" font-size="11" font-weight="600">{val}</text>'
        )
    return (
        f'<svg viewBox="0 0 {svg_w} {svg_h}" xmlns="http://www.w3.org/2000/svg" class="chart-svg">'
        + "".join(bars)
        + "</svg>"
    )


def _svg_pie_chart(data: List[Dict], colors: List[str] | None = None, donut: bool = False) -> str:
    if not data:
        return ""
    total = sum(d.get("value", 0) for d in data) or 1
    cx, cy, r = 150, 150, 120
    inner_r = 70 if donut else 0
    svg_w = 420

    paths = []
    angle = -math.pi / 2
    for i, d in enumerate(data):
        val = d.get("value", 0)
        sweep = (val / total) * 2 * math.pi
        x1 = cx + r * math.cos(angle)
        y1 = cy + r * math.sin(angle)
        x2 = cx + r * math.cos(angle + sweep)
        y2 = cy + r * math.sin(angle + sweep)
        large = 1 if sweep > math.pi else 0
        c = _chart_color(i, colors)

        if donut:
            ix1 = cx + inner_r * math.cos(angle)
            iy1 = cy + inner_r * math.sin(angle)
            ix2 = cx + inner_r * math.cos(angle + sweep)
            iy2 = cy + inner_r * math.sin(angle + sweep)
            path = (
                f"M {ix1},{iy1} L {x1},{y1} "
                f"A {r},{r} 0 {large} 1 {x2},{y2} "
                f"L {ix2},{iy2} "
                f"A {inner_r},{inner_r} 0 {large} 0 {ix1},{iy1} Z"
            )
        else:
            path = f"M {cx},{cy} L {x1},{y1} A {r},{r} 0 {large} 1 {x2},{y2} Z"

        paths.append(f'<path d="{path}" fill="{c}" opacity="0.9"/>')
        angle += sweep

    legend_x = cx * 2 + 20
    legend = []
    for i, d in enumerate(data):
        label = d.get("label", "")
        val = d.get("value", 0)
        pct = round(val / total * 100)
        ly = 30 + i * 26
        c = _chart_color(i, colors)
        legend.append(
            f'<rect x="{legend_x}" y="{ly}" width="12" height="12" rx="2" fill="{c}"/>'
            f'<text x="{legend_x + 18}" y="{ly + 11}" fill="#ccc" font-size="11">{_truncate(label, 14)} ({pct}%)</text>'
        )

    return (
        f'<svg viewBox="0 0 {svg_w} 310" xmlns="http://www.w3.org/2000/svg" class="chart-svg">'
        + "".join(paths) + "".join(legend)
        + "</svg>"
    )


def _svg_line_chart(data: List[Dict], colors: List[str] | None = None) -> str:
    if not data:
        return ""
    max_val = max((d.get("value", 0) for d in data), default=1) or 1
    n = len(data)
    svg_w, svg_h = 500, 260
    plot_h = 200
    pad_x, pad_y = 40, 10
    plot_w = svg_w - 2 * pad_x

    points = []
    for i, d in enumerate(data):
        val = d.get("value", 0)
        x = pad_x + (i / max(n - 1, 1)) * plot_w
        y = pad_y + plot_h - (val / max_val) * (plot_h - 20)
        points.append((x, y, val, d.get("label", "")))

    polyline = " ".join(f"{p[0]},{p[1]}" for p in points)
    c = _chart_color(0, colors)

    # Gradient fill under line
    fill_points = polyline + f" {points[-1][0]},{pad_y + plot_h} {points[0][0]},{pad_y + plot_h}"

    dots = []
    labels = []
    for x, y, val, label in points:
        dots.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{c}" stroke="#1a1a2e" stroke-width="2"/>')
        dots.append(f'<text x="{x}" y="{y - 10}" text-anchor="middle" fill="#fff" font-size="10" font-weight="600">{val}</text>')
        labels.append(f'<text x="{x}" y="{pad_y + plot_h + 18}" text-anchor="middle" fill="#aaa" font-size="9">{_truncate(label, 8)}</text>')

    return (
        f'<svg viewBox="0 0 {svg_w} {svg_h}" xmlns="http://www.w3.org/2000/svg" class="chart-svg">'
        f'<defs><linearGradient id="lfill" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{c}" stop-opacity="0.3"/>'
        f'<stop offset="100%" stop-color="{c}" stop-opacity="0.02"/>'
        f'</linearGradient></defs>'
        f'<line x1="{pad_x}" y1="{pad_y + plot_h}" x2="{svg_w - pad_x}" y2="{pad_y + plot_h}" stroke="#444" stroke-width="1"/>'
        f'<polygon points="{fill_points}" fill="url(#lfill)"/>'
        f'<polyline points="{polyline}" fill="none" stroke="{c}" stroke-width="2.5" stroke-linejoin="round"/>'
        + "".join(dots) + "".join(labels)
        + "</svg>"
    )


def _truncate(text: str, max_len: int) -> str:
    return text if len(text) <= max_len else text[:max_len - 1] + "…"


def _render_chart(slide: Dict[str, Any]) -> str:
    chart_type = slide.get("chart_type", "bar")
    data = slide.get("data", [])
    colors = slide.get("colors") or None

    renderers = {
        "bar": _svg_bar_chart,
        "horizontal-bar": _svg_horizontal_bar_chart,
        "pie": lambda d, c: _svg_pie_chart(d, c, donut=False),
        "donut": lambda d, c: _svg_pie_chart(d, c, donut=True),
        "line": _svg_line_chart,
    }
    renderer = renderers.get(chart_type, _svg_bar_chart)
    return f'<div class="chart-container">{renderer(data, colors)}</div>'


# ════════════════════════════════════════════
# Main generate_slides function
# ════════════════════════════════════════════

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

    Args:
        outline: JSON string con la estructura de la presentación:
                 {"title": "...", "slides": [{"title": "...", "type": "...", ...}]}
        context: Información adicional recopilada (fuentes, datos, etc.)
        _event_callback: Callback para emitir eventos (inyectado por el sistema)
    """
    logger.info("📊 generate_slides called", outline_length=len(outline))

    events_emitted = []

    def emit(event: str):
        events_emitted.append(event)
        if _event_callback:
            _event_callback(event)

    try:
        emit(create_thinking_event("Procesando solicitud de presentación...", status="start"))

        try:
            data = json.loads(outline)
            title = data.get("title", "Presentación")
            slides_data = data.get("slides", [])
        except json.JSONDecodeError as e:
            emit(create_thinking_event(f"Error parseando outline: {e}", status="error"))
            return {"success": False, "error": f"Invalid JSON outline: {e}", "events_emitted": events_emitted}

        if not slides_data:
            return {"success": False, "error": "No slides in outline", "events_emitted": events_emitted}

        emit(create_thinking_event(
            f"Outline recibido: {title}\n- {len(slides_data)} slides a generar",
            status="complete",
        ))
        emit(create_action_event(action_type="slides", title=f"Generando {len(slides_data)} slides", status="running"))

        html = _get_slides_css()

        for i, slide in enumerate(slides_data, 1):
            await asyncio.sleep(0.1)
            slide_html = _generate_slide_html(slide, i, len(slides_data))
            html += slide_html
            emit(create_artifact_event(artifact_type="slides", title=title, content=html, format="html"))
            logger.debug(f"Slide {i}/{len(slides_data)} generated")

        emit(create_action_event(action_type="slides", title=f"Generando {len(slides_data)} slides", status="completed"))

        slides_count = html.count('class="slide"')
        logger.info("✅ generate_slides completed", title=title, slides_count=slides_count, events=len(events_emitted))

        return {
            "success": True,
            "html": html,
            "title": title,
            "slides_count": slides_count,
            "events_emitted": events_emitted,
            "message": f"Presentación '{title}' generada con {slides_count} slides",
        }

    except Exception as e:
        logger.error(f"generate_slides error: {e}", exc_info=True)
        emit(create_action_event(action_type="slides", title="Error generando slides", status="error", description=str(e)))
        return {"success": False, "error": str(e), "events_emitted": events_emitted}


# ════════════════════════════════════════════
# CSS
# ════════════════════════════════════════════

def _get_slides_css() -> str:
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
.chart-container {
  margin: 20px 0;
  display: flex;
  justify-content: center;
}
.chart-svg {
  width: 100%;
  max-width: 500px;
  height: auto;
}
</style>
"""


# ════════════════════════════════════════════
# Slide HTML renderer
# ════════════════════════════════════════════

def _generate_slide_html(slide: Dict[str, Any], num: int, total: int) -> str:
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

    if badge:
        html_parts.append(f'  <span class="badge">{badge}</span>')

    if slide_type == "title":
        html_parts.append(f'  <h1>{title}</h1>')
    else:
        html_parts.append(f'  <h2>{title}</h2>')

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
            html_parts.append(
                f'    <div>'
                f'<div class="stat-value">{stat.get("value", "")}</div>'
                f'<div class="stat-label">{stat.get("label", "")}</div>'
                f'</div>'
            )
        html_parts.append('  </div>')

    if items:
        html_parts.append('  <div class="grid">')
        for item in items:
            html_parts.append(
                f'    <div class="card">'
                f'<div class="card-title">{item.get("title", "")}</div>'
                f'<div class="card-desc">{item.get("description", "")}</div>'
                f'</div>'
            )
        html_parts.append('  </div>')

    if quote:
        html_parts.append(f'  <div class="quote">"{quote}"</div>')
        if author:
            html_parts.append(f'  <p>— {author}</p>')

    # Chart rendering for type "chart"
    if slide_type == "chart" and slide.get("data"):
        html_parts.append(_render_chart(slide))

    html_parts.append('</div>\n')
    return '\n'.join(html_parts)


# ════════════════════════════════════════════
# Tool Definition
# ════════════════════════════════════════════

GENERATE_SLIDES_TOOL = {
    "id": "generate_slides",
    "name": "generate_slides",
    "description": """Genera una presentación HTML profesional con streaming progresivo.

Crea un outline JSON estructurado y llama a esta tool.

Formato del outline:
- title: Título de la presentación
- slides: Array de objetos slide

Tipos de slide disponibles:
- type "title": Slide de portada (h1)
- type "content": Texto libre
- type "bullets": Lista de puntos (bullets: [...])
- type "stats": Métricas grandes (stats: [{value, label}])
- type "cards": Tarjetas en grid (items: [{title, description}])
- type "quote": Cita (quote, author)
- type "chart": Gráfico SVG (chart_type, data: [{label, value}])

Tipos de gráfico (chart_type):
- "bar": Barras verticales (comparaciones)
- "horizontal-bar": Barras horizontales (rankings)
- "pie": Gráfico circular (distribución %)
- "donut": Anillo (distribución %)
- "line": Línea temporal (tendencias)

Opciones comunes:
- badge: Etiqueta como "INTRO", "DATOS" (opcional)
- content: Texto adicional (opcional)

Ejemplo con gráficos:
generate_slides(outline='{"title":"Ventas Q4","slides":[{"title":"Ventas Q4","type":"title","badge":"INFORME"},{"title":"Por Canal","type":"chart","chart_type":"pie","data":[{"label":"Online","value":45},{"label":"Retail","value":35},{"label":"B2B","value":20}]},{"title":"Evolución","type":"chart","chart_type":"bar","data":[{"label":"Oct","value":120},{"label":"Nov","value":150},{"label":"Dic","value":190}]},{"title":"Conclusiones","type":"bullets","bullets":["Crecimiento del 15%","Canal online líder"]}]}')""",
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
