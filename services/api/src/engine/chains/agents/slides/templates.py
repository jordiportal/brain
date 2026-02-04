"""Templates HTML para diferentes tipos de slides con layouts modernos."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class SlideOutline:
    """Estructura de una slide."""
    title: str
    type: str = "content"  # title, content, bullets, stats, comparison, quote, cards
    layout: str = ""  # slide-title, slide-split, slide-cards, slide-stats, slide-quote, slide-timeline
    content: Optional[str] = None
    badge: Optional[str] = None
    bullets: List[str] = field(default_factory=list)
    stats: List[Dict[str, str]] = field(default_factory=list)
    items: List[Dict[str, str]] = field(default_factory=list)
    quote: Optional[str] = None
    author: Optional[str] = None
    subtitle: Optional[str] = None  # Para slides de título


@dataclass
class PresentationOutline:
    """Outline completo de la presentación."""
    title: str
    slides: List[SlideOutline]
    theme: str = "dark"
    language: str = "es"
    generate_images: List[str] = field(default_factory=list)


def _clean_bullet(bullet) -> str:
    """Limpia un bullet, manejando diferentes formatos."""
    if bullet is None:
        return ""
    if isinstance(bullet, str):
        # Eliminar comillas y corchetes si están presentes
        return bullet.strip().strip('"\'[]')
    elif isinstance(bullet, list):
        # Si es una lista, unir elementos o tomar el primero
        if len(bullet) == 0:
            return ""
        if len(bullet) == 1:
            return _clean_bullet(bullet[0])
        return ", ".join(_clean_bullet(b) for b in bullet if b)
    elif isinstance(bullet, dict):
        # Si es un dict, extraer el texto
        return bullet.get("text", bullet.get("content", str(bullet)))
    return str(bullet)


def _parse_content_as_bullets(content) -> list:
    """Intenta extraer bullets de un contenido que puede ser string o lista."""
    if not content:
        return []
    
    # Si ya es una lista, procesarla directamente
    if isinstance(content, list):
        return [_clean_bullet(item) for item in content if item]
    
    if not isinstance(content, str):
        return []
    
    content = content.strip()
    
    # Si parece un array JSON
    if content.startswith("[") and content.endswith("]"):
        try:
            import json
            items = json.loads(content)
            if isinstance(items, list):
                return [_clean_bullet(item) for item in items if item]
        except:
            pass
    
    # Si tiene formato de lista con saltos de línea
    if "\n" in content:
        lines = [l.strip().lstrip("-•*").strip() for l in content.split("\n") if l.strip()]
        if len(lines) > 1:
            return lines
    
    return []


def generate_slide_html(slide: SlideOutline, image_url: Optional[str] = None) -> str:
    """
    Genera HTML para una slide individual con layouts modernos.
    
    Args:
        slide: SlideOutline con los datos
        image_url: URL de imagen opcional para la slide
        
    Returns:
        HTML string
    """
    # Determinar layout
    layout = slide.layout or _infer_layout(slide, image_url)
    
    # Usar generador específico según layout
    if layout == "slide-split" and image_url:
        return _generate_split_slide(slide, image_url)
    elif layout == "slide-cards" or (slide.type == "cards" and slide.items):
        return _generate_cards_slide(slide)
    elif layout == "slide-stats" or slide.type == "stats":
        return _generate_stats_slide(slide)
    elif layout == "slide-quote" or slide.type == "quote":
        return _generate_quote_slide(slide)
    elif layout == "slide-timeline":
        return _generate_timeline_slide(slide)
    elif layout == "slide-title" or slide.type == "title":
        return _generate_title_slide(slide, image_url)
    else:
        return _generate_default_slide(slide, image_url)


def _infer_layout(slide: SlideOutline, image_url: Optional[str]) -> str:
    """Infiere el layout más apropiado según el contenido."""
    if slide.type == "title":
        return "slide-title"
    if slide.type == "stats" or slide.stats:
        return "slide-stats"
    if slide.type == "quote" or slide.quote:
        return "slide-quote"
    if slide.type == "cards" or (slide.items and len(slide.items) >= 2):
        return "slide-cards"
    if image_url and (slide.bullets or slide.content):
        return "slide-split"
    return "slide-default"


def _generate_title_slide(slide: SlideOutline, image_url: Optional[str] = None) -> str:
    """Slide de título/portada."""
    parts = ['<div class="slide slide-title">']
    if slide.badge:
        parts.append(f'  <span class="badge">{slide.badge}</span>')
    parts.append(f'  <h1>{slide.title}</h1>')
    if slide.subtitle or slide.content:
        parts.append(f'  <p class="subtitle">{slide.subtitle or slide.content}</p>')
    if image_url:
        parts.append(f'  <div class="title-image"><img src="{image_url}" alt="" /></div>')
    parts.append('</div>\n')
    return '\n'.join(parts)


def _generate_split_slide(slide: SlideOutline, image_url: str) -> str:
    """Slide con contenido + imagen lado a lado."""
    bullets = [_clean_bullet(b) for b in slide.bullets if b] if slide.bullets else []
    if not bullets and slide.content:
        extracted = _parse_content_as_bullets(slide.content)
        if extracted:
            bullets = extracted
    
    parts = ['<div class="slide slide-split">']
    parts.append('  <div class="split-content">')
    if slide.badge:
        parts.append(f'    <span class="badge">{slide.badge}</span>')
    parts.append(f'    <h2>{slide.title}</h2>')
    if slide.content and not slide.content.startswith("["):
        parts.append(f'    <p>{slide.content}</p>')
    if bullets:
        parts.append('    <ul class="features">')
        for bullet in bullets:
            if bullet:
                parts.append(f'      <li>{bullet}</li>')
        parts.append('    </ul>')
    parts.append('  </div>')
    parts.append('  <div class="split-visual">')
    parts.append(f'    <img src="{image_url}" alt="{slide.title}" />')
    parts.append('  </div>')
    parts.append('</div>\n')
    return '\n'.join(parts)


def _generate_cards_slide(slide: SlideOutline) -> str:
    """Slide con grid de cards."""
    parts = ['<div class="slide slide-cards">']
    if slide.badge:
        parts.append(f'  <span class="badge">{slide.badge}</span>')
    parts.append(f'  <h2>{slide.title}</h2>')
    parts.append('  <div class="cards-grid">')
    for item in slide.items:
        icon = item.get("icon", "✨")
        title = item.get("title", "")
        text = item.get("text", item.get("description", ""))
        parts.append(f'''    <div class="card">
      <div class="card-icon">{icon}</div>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>''')
    parts.append('  </div>')
    parts.append('</div>\n')
    return '\n'.join(parts)


def _generate_stats_slide(slide: SlideOutline) -> str:
    """Slide con números/métricas grandes."""
    parts = ['<div class="slide slide-stats">']
    if slide.badge:
        parts.append(f'  <span class="badge">{slide.badge}</span>')
    parts.append(f'  <h2>{slide.title}</h2>')
    parts.append('  <div class="stats-grid">')
    for stat in slide.stats:
        value = stat.get("value", "")
        label = stat.get("label", "")
        parts.append(f'''    <div class="stat">
      <span class="stat-number">{value}</span>
      <span class="stat-label">{label}</span>
    </div>''')
    parts.append('  </div>')
    parts.append('</div>\n')
    return '\n'.join(parts)


def _generate_quote_slide(slide: SlideOutline) -> str:
    """Slide con cita/testimonio."""
    parts = ['<div class="slide slide-quote">']
    parts.append('  <blockquote>')
    parts.append(f'    <p>"{slide.quote or slide.content}"</p>')
    if slide.author:
        parts.append('    <footer>')
        parts.append(f'      <cite>{slide.author}</cite>')
        parts.append('    </footer>')
    parts.append('  </blockquote>')
    parts.append('</div>\n')
    return '\n'.join(parts)


def _generate_timeline_slide(slide: SlideOutline) -> str:
    """Slide con timeline/evolución."""
    parts = ['<div class="slide slide-timeline">']
    if slide.badge:
        parts.append(f'  <span class="badge">{slide.badge}</span>')
    parts.append(f'  <h2>{slide.title}</h2>')
    parts.append('  <div class="timeline">')
    for item in slide.items:
        year = item.get("year", item.get("date", ""))
        title = item.get("title", "")
        text = item.get("text", item.get("description", ""))
        parts.append(f'''    <div class="timeline-item">
      <span class="timeline-year">{year}</span>
      <h3>{title}</h3>
      <p>{text}</p>
    </div>''')
    parts.append('  </div>')
    parts.append('</div>\n')
    return '\n'.join(parts)


def _generate_default_slide(slide: SlideOutline, image_url: Optional[str] = None) -> str:
    """Slide por defecto con bullets."""
    bullets = [_clean_bullet(b) for b in slide.bullets if b] if slide.bullets else []
    if not bullets and slide.content:
        extracted = _parse_content_as_bullets(slide.content)
        if extracted:
            bullets = extracted
    
    parts = ['<div class="slide">']
    if slide.badge:
        parts.append(f'  <span class="badge">{slide.badge}</span>')
    parts.append(f'  <h2>{slide.title}</h2>')
    
    if slide.content and not slide.content.startswith("[") and not bullets:
        parts.append(f'  <p>{slide.content}</p>')
    
    if bullets:
        parts.append('  <ul class="features">')
        for bullet in bullets:
            if bullet:
                parts.append(f'    <li>{bullet}</li>')
        parts.append('  </ul>')
    
    if image_url:
        parts.append(f'  <div class="slide-image">')
        parts.append(f'    <img src="{image_url}" alt="Ilustración" />')
        parts.append(f'  </div>')
    
    parts.append('</div>\n')
    return '\n'.join(parts)
