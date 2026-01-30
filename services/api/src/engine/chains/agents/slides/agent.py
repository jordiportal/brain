"""
Slides Agent - Subagente para generación de presentaciones HTML.

Genera presentaciones con Brain Events para Open WebUI.
"""

import json
import time
from typing import Optional, List, Dict, Any

import structlog

from ..base import BaseSubAgent, SubAgentResult
from .styles import SLIDES_CSS
from .templates import SlideOutline, PresentationOutline, generate_slide_html
from .events import thinking_event, action_event, artifact_event

logger = structlog.get_logger()


SLIDES_SYSTEM_PROMPT = """You are a specialized Presentation Designer Agent.

# INSTRUCTIONS

1. Analyze the presentation request carefully
2. Determine the best structure: number of slides, flow, key messages
3. Create professional, visually appealing HTML presentations
4. Ensure content is concise and impactful

# SLIDE TYPES

- **title**: Opening slide with main title and badge
- **content**: General content with text/description
- **bullets**: List of key points (3-5 bullets ideal)
- **stats**: Numeric data with icons
- **comparison**: Side-by-side comparison (pros/cons, before/after)
- **quote**: Inspirational or key quote

# DESIGN PRINCIPLES

- Keep text minimal (max 5-6 words per bullet)
- Use visual hierarchy: titles > subtitles > content
- Include badges/tags to categorize sections
- Balance text with whitespace
- 5-8 slides is optimal for most presentations

# STRUCTURE TEMPLATE

1. Title slide (hook the audience)
2. Problem/Context (why this matters)
3. Key points (2-3 content slides)
4. Data/Evidence (stats or comparison)
5. Solution/Takeaway
6. Conclusion/Call to action

# EXAMPLES

User: "Presentación sobre IA"
→ Structure: Intro, ¿Qué es IA?, Aplicaciones, Impacto, Futuro, Conclusión

User: "Pitch de startup"  
→ Structure: Hook, Problema, Solución, Mercado, Modelo, Equipo, Ask
"""


class SlidesAgent(BaseSubAgent):
    """Subagente para generación de presentaciones HTML."""
    
    id = "slides_agent"
    name = "Slides Agent"
    description = "Genera presentaciones HTML profesionales con streaming"
    version = "2.0.0"
    domain_tools = []  # No usa tools externas, genera HTML directamente
    system_prompt = SLIDES_SYSTEM_PROMPT
    
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
        Genera presentación desde outline JSON o texto.
        
        La respuesta incluye Brain Events para Open WebUI.
        """
        start_time = time.time()
        logger.info("📊 SlidesAgent executing", task_length=len(task))
        
        response_parts = []
        
        try:
            # Thinking event
            response_parts.append(thinking_event(
                "Procesando solicitud de presentación...",
                status="start"
            ))
            
            # Parsear outline
            outline = self._parse_outline(task)
            
            if not outline:
                if llm_url and model:
                    response_parts.append(thinking_event(
                        "Creando estructura con IA..."
                    ))
                    outline = await self._create_outline_llm(
                        task, context, llm_url, model, provider_type, api_key
                    )
                else:
                    return SubAgentResult(
                        success=False,
                        response="Se requiere outline JSON o configuración LLM",
                        agent_id=self.id,
                        agent_name=self.name,
                        error="No outline provided"
                    )
            
            response_parts.append(thinking_event(
                f"Outline: {outline.title}\n- {len(outline.slides)} slides",
                status="complete"
            ))
            
            # Action: generando
            response_parts.append(action_event(
                action_type="slides",
                title=f"Generando {len(outline.slides)} slides",
                status="running"
            ))
            
            # Generar HTML
            html = SLIDES_CSS
            for slide in outline.slides:
                html += generate_slide_html(slide)
            
            slides_count = html.count('class="slide"')
            
            # Artifact event
            response_parts.append(artifact_event(
                html_content=html,
                title=outline.title
            ))
            
            # Action: completado
            response_parts.append(action_event(
                action_type="slides",
                title=f"Generando {len(outline.slides)} slides",
                status="completed"
            ))
            
            # Mensaje final
            response_parts.append(f"\n✅ **{outline.title}**\n📊 {slides_count} slides\n")
            
            return SubAgentResult(
                success=True,
                response="".join(response_parts),
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
                response=f"Error: {str(e)}",
                agent_id=self.id,
                agent_name=self.name,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
    
    def _parse_outline(self, task: str) -> Optional[PresentationOutline]:
        """Intenta parsear task como JSON outline."""
        try:
            data = json.loads(task)
            if not isinstance(data, dict) or "title" not in data:
                return None
            
            slides = []
            for s in data.get("slides", []):
                # Asegurar que bullets sea una lista de strings
                raw_bullets = s.get("bullets", [])
                if isinstance(raw_bullets, str):
                    # Si es un string, intentar parsearlo como JSON
                    try:
                        raw_bullets = json.loads(raw_bullets)
                    except:
                        raw_bullets = [raw_bullets]
                if not isinstance(raw_bullets, list):
                    raw_bullets = []
                
                # Limpiar cada bullet
                clean_bullets = []
                for b in raw_bullets:
                    if isinstance(b, str) and b.strip():
                        clean_bullets.append(b.strip())
                    elif isinstance(b, dict):
                        text = b.get("text", b.get("content", ""))
                        if text:
                            clean_bullets.append(str(text).strip())
                
                # Asegurar que content sea string
                content = s.get("content")
                if isinstance(content, list):
                    # Si content es una lista, convertir a bullets
                    if not clean_bullets:
                        clean_bullets = [str(c).strip() for c in content if c]
                    content = None
                elif content:
                    content = str(content)
                
                slides.append(SlideOutline(
                    title=str(s.get("title", "")),
                    type=s.get("type", "content"),
                    content=content,
                    badge=s.get("badge"),
                    bullets=clean_bullets,
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
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Could not parse outline: {e}")
            return None
    
    async def _create_outline_llm(
        self,
        task: str,
        context: Optional[str],
        llm_url: str,
        model: str,
        provider_type: str,
        api_key: Optional[str]
    ) -> PresentationOutline:
        """Crea outline usando LLM."""
        from ...llm_utils import call_llm
        
        prompt = f"""Crea una presentación profesional como JSON.

TEMA: {task}
{f"CONTEXTO: {context}" if context else ""}

FORMATO JSON REQUERIDO:
{{
  "title": "Título de la Presentación",
  "slides": [
    {{"title": "Slide 1", "type": "title", "badge": "INICIO", "content": "Subtítulo opcional"}},
    {{"title": "Slide 2", "type": "bullets", "badge": "PUNTOS CLAVE", "bullets": ["Punto 1", "Punto 2", "Punto 3"]}},
    {{"title": "Slide 3", "type": "content", "content": "Texto descriptivo aquí"}},
    {{"title": "Conclusión", "type": "bullets", "badge": "RESUMEN", "bullets": ["Conclusión 1", "Conclusión 2"]}}
  ]
}}

TIPOS DE SLIDE:
- title: Slide de título (primera slide)
- bullets: Lista de puntos (usar array "bullets", NO "content")
- content: Texto descriptivo
- stats: Estadísticas con "stats": [{{"value": "100%", "label": "Efectividad"}}]
- quote: Cita con "quote" y "author"

REGLAS:
1. Para listas de puntos, SIEMPRE usar "type": "bullets" con "bullets": ["item1", "item2", ...]
2. NUNCA poner listas dentro de "content" - usar "bullets" 
3. Cada bullet debe ser texto simple, máximo 10 palabras
4. 5-7 slides total
5. Incluir badge descriptivo en cada slide

Responde SOLO con el JSON válido, sin texto adicional."""
        
        messages = [
            {"role": "system", "content": "Eres un diseñador de presentaciones. Responde SOLO con JSON válido."},
            {"role": "user", "content": prompt}
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
        for prefix in ["```json", "```"]:
            if response.startswith(prefix):
                response = response[len(prefix):]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        logger.info(f"LLM response for slides: {response[:500]}...")
        
        outline = self._parse_outline(response)
        
        if not outline:
            logger.warning("Could not parse LLM response as outline, using fallback")
            # Fallback básico
            outline = PresentationOutline(
                title="Presentación",
                slides=[
                    SlideOutline(title="Introducción", type="title", badge="INICIO"),
                    SlideOutline(title="Contenido", type="content", content=task[:200])
                ]
            )
        
        return outline
