"""Templates HTML para diferentes tipos de slides."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class SlideOutline:
    """Estructura de una slide."""
    title: str
    type: str = "content"  # title, content, bullets, stats, comparison, quote
    content: Optional[str] = None
    badge: Optional[str] = None
    bullets: List[str] = field(default_factory=list)
    stats: List[Dict[str, str]] = field(default_factory=list)
    items: List[Dict[str, str]] = field(default_factory=list)
    quote: Optional[str] = None
    author: Optional[str] = None


@dataclass
class PresentationOutline:
    """Outline completo de la presentación."""
    title: str
    slides: List[SlideOutline]
    theme: str = "dark"
    language: str = "es"


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


def generate_slide_html(slide: SlideOutline) -> str:
    """
    Genera HTML para una slide individual.
    
    Args:
        slide: SlideOutline con los datos
        
    Returns:
        HTML string
    """
    parts = ['<div class="slide">']
    
    # Badge
    if slide.badge:
        parts.append(f'  <span class="badge">{slide.badge}</span>')
    
    # Título
    if slide.type == "title":
        parts.append(f'  <h1>{slide.title}</h1>')
    else:
        parts.append(f'  <h2>{slide.title}</h2>')
    
    # Obtener bullets (pueden venir en bullets o en content)
    bullets = [_clean_bullet(b) for b in slide.bullets if b] if slide.bullets else []
    
    # Si no hay bullets pero content parece una lista, extraerlos
    if not bullets and slide.content:
        extracted = _parse_content_as_bullets(slide.content)
        if extracted:
            bullets = extracted
    
    # Contenido según tipo
    if slide.type == "title":
        if slide.content and not slide.content.startswith("["):
            parts.append(f'  <p>{slide.content}</p>')
    
    elif slide.type == "bullets" or bullets:
        # Si hay contenido que no es una lista, mostrarlo primero
        if slide.content and not slide.content.startswith("["):
            parts.append(f'  <p>{slide.content}</p>')
        if bullets:
            parts.append('  <ul>')
            for bullet in bullets:
                if bullet:  # Ignorar bullets vacíos
                    parts.append(f'    <li>{bullet}</li>')
            parts.append('  </ul>')
    
    elif slide.type == "stats" and slide.stats:
        parts.append('  <div class="stats">')
        for stat in slide.stats:
            parts.append(f'''    <div>
      <div class="stat-value">{stat.get("value", "")}</div>
      <div class="stat-label">{stat.get("label", "")}</div>
    </div>''')
        parts.append('  </div>')
    
    elif slide.type == "comparison" or slide.items:
        parts.append('  <div class="grid">')
        for item in slide.items:
            parts.append(f'''    <div class="card">
      <div class="card-title">{item.get("title", "")}</div>
      <div class="card-desc">{item.get("description", "")}</div>
    </div>''')
        parts.append('  </div>')
    
    elif slide.type == "quote" and slide.quote:
        parts.append(f'  <div class="quote">"{slide.quote}"</div>')
        if slide.author:
            parts.append(f'  <p>— {slide.author}</p>')
    
    elif slide.content and not slide.content.startswith("["):
        parts.append(f'  <p>{slide.content}</p>')
    
    parts.append('</div>\n')
    
    return '\n'.join(parts)
