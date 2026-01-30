"""
Slides Agent - Subagente especializado en generación de presentaciones

Este agente genera presentaciones en formato HTML compatible con Open WebUI.
Emite Brain Events (markers HTML) para comunicar el progreso al frontend.

Flujo:
1. Recibe outline/esquema de la presentación del orquestrador
2. Genera slides HTML una a una
3. Emite eventos: thinking → action → sources → artifact

Formato de salida:
<!--BRAIN_EVENT:{"type":"artifact","artifact_type":"slides",...}-->
"""

import json
import base64
import time
from typing import Optional, Dict, Any, List, AsyncGenerator
from dataclasses import dataclass, field

import structlog

from .base_agent import BaseSubAgent, SubAgentResult

logger = structlog.get_logger()


# ============================================
# Constantes y Templates
# ============================================

SLIDES_CSS = """
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
.code {
  background: rgba(0,0,0,0.3);
  padding: 16px;
  border-radius: 8px;
  font-family: monospace;
  overflow-x: auto;
}
</style>
"""

SLIDES_AGENT_PROMPT = """You are an expert presentation designer. Create beautiful, professional HTML slides.

# INPUT FORMAT
You receive a JSON outline with:
- title: Presentation title
- slides: Array of slide objects with:
  - title: Slide title
  - type: "title" | "content" | "stats" | "bullets" | "comparison" | "quote" | "conclusion"
  - content: Main content or bullet points
  - badge: Optional badge text (like "INTRO", "KEY POINT", etc.)
  - stats: Optional stats array [{value, label}] for stats slides
  - items: Optional grid items [{title, description}] for comparison slides

# OUTPUT REQUIREMENTS
1. Generate clean, semantic HTML
2. Use the provided CSS classes: .slide, .badge, .highlight, .stats, .stat-value, .stat-label, .grid, .card, .card-title, .card-desc, .quote, .code
3. Each slide is a <div class="slide">
4. Use appropriate HTML tags: <h1> for main titles, <h2> for slide titles, <ul>/<ol> for lists
5. Make content concise but impactful
6. Add visual hierarchy with badges and highlights

# SLIDE TYPE TEMPLATES

## Title Slide
<div class="slide">
  <span class="badge">PRESENTACIÓN</span>
  <h1>Main Title Here</h1>
  <p>Subtitle or description</p>
</div>

## Content Slide
<div class="slide">
  <span class="badge">SECCIÓN</span>
  <h2>Slide Title</h2>
  <p>Content paragraph with <span class="highlight">highlighted text</span>.</p>
</div>

## Bullets Slide
<div class="slide">
  <h2>Key Points</h2>
  <ul>
    <li><strong>Point 1:</strong> Description</li>
    <li><strong>Point 2:</strong> Description</li>
  </ul>
</div>

## Stats Slide
<div class="slide">
  <h2>By the Numbers</h2>
  <div class="stats">
    <div><div class="stat-value">85%</div><div class="stat-label">Accuracy</div></div>
    <div><div class="stat-value">10x</div><div class="stat-label">Faster</div></div>
  </div>
</div>

## Comparison/Grid Slide
<div class="slide">
  <h2>Comparison</h2>
  <div class="grid">
    <div class="card"><div class="card-title">Option A</div><div class="card-desc">Description</div></div>
    <div class="card"><div class="card-title">Option B</div><div class="card-desc">Description</div></div>
  </div>
</div>

## Quote Slide
<div class="slide">
  <h2>Insight</h2>
  <div class="quote">"The quote text here."</div>
  <p>— Author Name</p>
</div>

Generate ONLY the HTML for slides, no explanations.
"""


@dataclass
class SlideOutline:
    """Estructura de una slide en el outline."""
    title: str
    type: str = "content"
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


# ============================================
# Brain Event Helpers
# ============================================

def create_brain_event(event_type: str, **kwargs) -> str:
    """Crea un marker de Brain Event."""
    event = {"type": event_type, **kwargs}
    return f"\n<!--BRAIN_EVENT:{json.dumps(event, ensure_ascii=False)}-->\n"


def create_thinking_event(content: str, status: str = "progress") -> str:
    """Evento de thinking/razonamiento."""
    return create_brain_event("thinking", content=content, status=status)


def create_action_event(
    action_type: str,
    title: str,
    status: str,
    description: Optional[str] = None,
    results_count: Optional[int] = None
) -> str:
    """Evento de acción."""
    event = {
        "type": "action",
        "action_type": action_type,
        "title": title,
        "status": status
    }
    if description:
        event["description"] = description
    if results_count is not None:
        event["results_count"] = results_count
    return f"\n<!--BRAIN_EVENT:{json.dumps(event, ensure_ascii=False)}-->\n"


def create_sources_event(sources: List[Dict[str, str]]) -> str:
    """Evento de fuentes consultadas."""
    return create_brain_event("sources", sources=sources)


def create_artifact_event(html_content: str, title: str) -> str:
    """Evento de artifact (slides) con contenido en base64."""
    content_b64 = base64.b64encode(html_content.encode("utf-8")).decode("ascii")
    return create_brain_event(
        "artifact",
        artifact_type="slides",
        title=title,
        content_base64=content_b64,
        format="html"
    )


# ============================================
# Slides Agent
# ============================================

class SlidesAgent(BaseSubAgent):
    """
    Subagente especializado en generación de presentaciones HTML.
    
    Flujo típico:
    1. Orquestrador busca información y crea outline
    2. SlidesAgent recibe el outline
    3. Genera HTML slide por slide
    4. Emite Brain Events para el frontend
    """
    
    id = "slides_agent"
    name = "Slides Agent"
    description = "Genera presentaciones HTML profesionales con streaming progresivo"
    version = "1.0.0"
    
    domain_tools = []  # No usa tools externas, genera HTML directamente
    
    system_prompt = SLIDES_AGENT_PROMPT
    
    def __init__(self):
        super().__init__()
    
    async def execute(
        self,
        task: str,
        context: Optional[str] = None,
        llm_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_type: str = "ollama",
        api_key: Optional[str] = None
    ) -> SubAgentResult:
        """
        Ejecuta la generación de presentación.
        
        La respuesta incluye Brain Events embebidos como markers HTML
        para que Open WebUI los procese correctamente.
        
        Args:
            task: Puede ser:
                - JSON string con el outline completo
                - Texto describiendo la presentación (requiere LLM)
            context: Contexto adicional o fuentes
        """
        start_time = time.time()
        
        logger.info(
            "📊 SlidesAgent executing",
            task_length=len(task),
            has_context=bool(context)
        )
        
        response_parts = []
        
        try:
            # Evento thinking
            response_parts.append(create_thinking_event(
                "Procesando solicitud de presentación...",
                status="start"
            ))
            
            # Intentar parsear como JSON outline
            outline = self._parse_outline(task)
            
            if not outline:
                # Necesita LLM para crear outline
                if not llm_url or not model:
                    return SubAgentResult(
                        success=False,
                        response="Se requiere LLM para generar presentación desde texto. Pasa un outline JSON estructurado.",
                        agent_id=self.id,
                        agent_name=self.name,
                        error="LLM not configured or invalid outline"
                    )
                
                response_parts.append(create_thinking_event(
                    "Creando estructura de la presentación..."
                ))
                
                outline = await self._create_outline_with_llm(
                    task=task,
                    context=context,
                    llm_url=llm_url,
                    model=model,
                    provider_type=provider_type,
                    api_key=api_key
                )
            
            response_parts.append(create_thinking_event(
                f"Outline: {outline.title}\n- {len(outline.slides)} slides",
                status="complete"
            ))
            
            # Evento action - generando slides
            response_parts.append(create_action_event(
                action_type="slides",
                title=f"Generando {len(outline.slides)} slides",
                status="running"
            ))
            
            # Generar HTML
            html = await self._generate_from_outline(outline)
            slides_count = html.count('class="slide"')
            
            # Evento artifact con el HTML
            response_parts.append(create_artifact_event(
                html_content=html,
                title=outline.title
            ))
            
            # Evento action completado
            response_parts.append(create_action_event(
                action_type="slides",
                title=f"Generando {len(outline.slides)} slides",
                status="completed"
            ))
            
            # Mensaje final
            response_parts.append(f"\n✅ **Presentación generada:** {outline.title}\n")
            response_parts.append(f"📊 {slides_count} slides creadas\n")
            
            # Construir respuesta completa con todos los Brain Events
            full_response = "".join(response_parts)
            
            return SubAgentResult(
                success=True,
                response=full_response,
                agent_id=self.id,
                agent_name=self.name,
                tools_used=["slides_generator"],
                data={
                    "html": html,
                    "slides_count": slides_count,
                    "title": outline.title
                },
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
            
        except Exception as e:
            logger.error(f"SlidesAgent error: {e}", exc_info=True)
            return SubAgentResult(
                success=False,
                response=f"Error generando presentación: {str(e)}",
                agent_id=self.id,
                agent_name=self.name,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
    
    async def stream_execute(
        self,
        task: str,
        context: Optional[str] = None,
        llm_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_type: str = "ollama",
        api_key: Optional[str] = None,
        sources: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Genera presentación con streaming de Brain Events.
        
        Yields:
            Strings con Brain Event markers
        """
        logger.info(
            "📊 SlidesAgent streaming",
            task_length=len(task)
        )
        
        # 1. Thinking event
        yield create_thinking_event(
            f"Analizando solicitud de presentación...",
            status="start"
        )
        
        try:
            outline = self._parse_outline(task)
            
            if not outline:
                yield create_thinking_event(
                    "Generando estructura de la presentación con IA..."
                )
                
                if not llm_url or not model:
                    yield "Error: Se requiere LLM para generar desde texto\n"
                    return
                
                # Generar outline con LLM
                outline = await self._create_outline_with_llm(
                    task=task,
                    context=context,
                    llm_url=llm_url,
                    model=model,
                    provider_type=provider_type,
                    api_key=api_key
                )
            
            yield create_thinking_event(
                f"Outline creado: {outline.title}\n"
                f"- {len(outline.slides)} slides planificadas",
                status="complete"
            )
            
            # 2. Sources event (si hay)
            if sources:
                yield create_sources_event(sources)
            
            # 3. Action: Generando slides
            yield create_action_event(
                action_type="slides",
                title=f"Generando {len(outline.slides)} slides",
                status="running"
            )
            
            # 4. Generar slides progresivamente
            slides_html = SLIDES_CSS
            
            for i, slide in enumerate(outline.slides, 1):
                yield f"📄 Generando slide {i}/{len(outline.slides)}...\n"
                
                slide_html = self._generate_slide_html(slide, i, len(outline.slides))
                slides_html += slide_html
                
                # Emitir artifact acumulativo
                yield create_artifact_event(
                    html_content=slides_html,
                    title=outline.title
                )
                
                # Pequeña pausa para UX
                import asyncio
                await asyncio.sleep(0.3)
            
            # 5. Completar
            yield create_action_event(
                action_type="slides",
                title=f"Generando {len(outline.slides)} slides",
                status="completed"
            )
            
            yield f"\n✅ **Presentación completada:** {outline.title}\n"
            yield f"📊 {len(outline.slides)} slides generadas\n"
            
        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"\n❌ Error: {str(e)}\n"
    
    def _parse_outline(self, task: str) -> Optional[PresentationOutline]:
        """Intenta parsear el task como JSON outline."""
        try:
            data = json.loads(task)
            
            if not isinstance(data, dict) or "title" not in data:
                return None
            
            slides = []
            for s in data.get("slides", []):
                slides.append(SlideOutline(
                    title=s.get("title", ""),
                    type=s.get("type", "content"),
                    content=s.get("content"),
                    badge=s.get("badge"),
                    bullets=s.get("bullets", []),
                    stats=s.get("stats", []),
                    items=s.get("items", []),
                    quote=s.get("quote"),
                    author=s.get("author")
                ))
            
            return PresentationOutline(
                title=data["title"],
                slides=slides,
                theme=data.get("theme", "dark"),
                language=data.get("language", "es")
            )
            
        except (json.JSONDecodeError, TypeError):
            return None
    
    async def _generate_from_outline(self, outline: PresentationOutline) -> str:
        """Genera HTML desde un outline estructurado."""
        html = SLIDES_CSS
        
        for i, slide in enumerate(outline.slides, 1):
            html += self._generate_slide_html(slide, i, len(outline.slides))
        
        return html
    
    def _generate_slide_html(
        self,
        slide: SlideOutline,
        slide_num: int,
        total_slides: int
    ) -> str:
        """Genera HTML para una slide individual."""
        
        html_parts = ['<div class="slide">']
        
        # Badge
        if slide.badge:
            html_parts.append(f'  <span class="badge">{slide.badge}</span>')
        
        # Título (h1 para slide de título, h2 para el resto)
        if slide.type == "title":
            html_parts.append(f'  <h1>{slide.title}</h1>')
        else:
            html_parts.append(f'  <h2>{slide.title}</h2>')
        
        # Contenido según tipo
        if slide.type == "title" and slide.content:
            html_parts.append(f'  <p>{slide.content}</p>')
        
        elif slide.type == "bullets" or slide.bullets:
            if slide.content:
                html_parts.append(f'  <p>{slide.content}</p>')
            html_parts.append('  <ul>')
            for bullet in slide.bullets:
                html_parts.append(f'    <li>{bullet}</li>')
            html_parts.append('  </ul>')
        
        elif slide.type == "stats" and slide.stats:
            html_parts.append('  <div class="stats">')
            for stat in slide.stats:
                html_parts.append(f'''    <div>
      <div class="stat-value">{stat.get("value", "")}</div>
      <div class="stat-label">{stat.get("label", "")}</div>
    </div>''')
            html_parts.append('  </div>')
        
        elif slide.type == "comparison" or slide.items:
            html_parts.append('  <div class="grid">')
            for item in slide.items:
                html_parts.append(f'''    <div class="card">
      <div class="card-title">{item.get("title", "")}</div>
      <div class="card-desc">{item.get("description", "")}</div>
    </div>''')
            html_parts.append('  </div>')
        
        elif slide.type == "quote" and slide.quote:
            html_parts.append(f'  <div class="quote">"{slide.quote}"</div>')
            if slide.author:
                html_parts.append(f'  <p>— {slide.author}</p>')
        
        elif slide.content:
            # Contenido genérico
            html_parts.append(f'  <p>{slide.content}</p>')
        
        html_parts.append('</div>\n')
        
        return '\n'.join(html_parts)
    
    async def _generate_with_llm(
        self,
        task: str,
        context: Optional[str],
        llm_url: str,
        model: str,
        provider_type: str,
        api_key: Optional[str]
    ) -> str:
        """Genera HTML usando LLM para crear slides."""
        from ..llm_utils import call_llm
        
        # Construir prompt
        full_prompt = f"""Create an HTML presentation for the following request.

REQUEST: {task}

{f"ADDITIONAL CONTEXT: {context}" if context else ""}

Follow the slide templates in your instructions.
Generate 5-8 slides with appropriate types (title, content, bullets, stats, etc.)
Start with the CSS styles block, then each slide.
Output ONLY HTML, no explanations."""

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": full_prompt}
        ]
        
        html = await call_llm(
            llm_url=llm_url,
            model=model,
            messages=messages,
            temperature=0.7,
            provider_type=provider_type,
            api_key=api_key
        )
        
        # Limpiar y validar
        html = html.strip()
        if not html.startswith("<style>"):
            html = SLIDES_CSS + html
        
        return html
    
    async def _create_outline_with_llm(
        self,
        task: str,
        context: Optional[str],
        llm_url: str,
        model: str,
        provider_type: str,
        api_key: Optional[str]
    ) -> PresentationOutline:
        """Crea un outline estructurado usando LLM."""
        from ..llm_utils import call_llm
        
        outline_prompt = f"""Create a presentation outline as JSON for the following request.

REQUEST: {task}

{f"ADDITIONAL CONTEXT: {context}" if context else ""}

Output a JSON object with this structure:
{{
  "title": "Presentation Title",
  "slides": [
    {{"title": "Welcome", "type": "title", "content": "Subtitle", "badge": "INTRO"}},
    {{"title": "Overview", "type": "bullets", "bullets": ["Point 1", "Point 2"]}},
    {{"title": "Statistics", "type": "stats", "stats": [{{"value": "85%", "label": "Accuracy"}}]}},
    {{"title": "Comparison", "type": "comparison", "items": [{{"title": "A", "description": "..."}}]}},
    {{"title": "Conclusion", "type": "content", "content": "Summary", "badge": "RECAP"}}
  ]
}}

Use 5-8 slides with varied types. Output ONLY valid JSON."""

        messages = [
            {"role": "system", "content": "You are a presentation structure expert. Output only valid JSON."},
            {"role": "user", "content": outline_prompt}
        ]
        
        response = await call_llm(
            llm_url=llm_url,
            model=model,
            messages=messages,
            temperature=0.5,
            provider_type=provider_type,
            api_key=api_key
        )
        
        # Limpiar JSON
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        outline = self._parse_outline(response)
        
        if not outline:
            # Fallback: outline básico
            outline = PresentationOutline(
                title="Presentación",
                slides=[
                    SlideOutline(title="Introducción", type="title", badge="INICIO"),
                    SlideOutline(title="Contenido", type="content", content=task[:200])
                ]
            )
        
        return outline


# Registrar en el registry de subagentes
def register_slides_agent():
    """Registra el SlidesAgent en el registry."""
    from .base_agent import subagent_registry
    
    if not subagent_registry.get("slides_agent"):
        agent = SlidesAgent()
        subagent_registry.register(agent)
        logger.info("✅ SlidesAgent registered")
    
    return subagent_registry.get("slides_agent")
