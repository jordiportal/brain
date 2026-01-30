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


SLIDES_SYSTEM_PROMPT = """You are a specialized Presentation DESIGNER Agent.

# TU ROL

Eres un DISEÑADOR VISUAL de presentaciones. Tu trabajo es:
1. Recibir un OUTLINE estructurado del agente principal
2. Transformarlo en HTML visualmente atractivo
3. Decidir qué elementos visuales añadir (imágenes, iconos, stats)
4. Crear una experiencia visual profesional

# PRINCIPIOS DE DISEÑO

1. **Jerarquía Visual**
   - Títulos grandes y llamativos
   - Subtítulos que guían al ojo
   - Contenido secundario más pequeño
   
2. **Minimalismo**
   - Máximo 5 palabras por bullet
   - Una idea por slide
   - Mucho espacio en blanco
   
3. **Consistencia**
   - Mismo estilo de badges
   - Colores coherentes
   - Tipografía uniforme

4. **Impacto Visual**
   - Números grandes para estadísticas
   - Imágenes cuando aporten valor
   - Gradientes y sombras sutiles

# TIPOS DE SLIDE

| Tipo | Uso | Elementos |
|------|-----|-----------|
| title | Primera slide | Título grande, badge, subtítulo opcional |
| bullets | Listas | 3-5 puntos cortos, badge |
| stats | Datos | 2-4 números con labels |
| quote | Citas | Texto en cursiva, autor |
| comparison | Comparar | 2 columnas: antes/después, pros/cons |
| image | Visual | Imagen generada + caption |

# CUÁNDO AÑADIR IMÁGENES

Añade imágenes cuando:
- El tema es visual (productos, lugares, conceptos abstractos)
- Se puede ilustrar un concepto
- La slide necesita más impacto

NO añadas imágenes cuando:
- Es una lista de datos/hechos
- El texto ya es suficiente
- Sería decorativo sin aportar

# ESTRUCTURA IDEAL

```
1. TÍTULO - Hook que capture atención
2. CONTEXTO - Por qué importa (bullets o contenido)
3-4. DESARROLLO - Puntos clave (bullets, stats)
5. VISUAL - Imagen o comparación (si aplica)
6. CONCLUSIÓN - Call to action o resumen
```

# FORMATO JSON QUE RECIBIRÁS

```json
{
  "title": "Título",
  "slides": [
    {"title": "...", "type": "title|bullets|stats|quote", "badge": "...", "bullets": [...]}
  ],
  "generate_images": ["descripción imagen 1", "descripción imagen 2"]
}
```

Si recibes `generate_images`, generaré esas imágenes para incluirlas en las slides apropiadas.
"""


class SlidesAgent(BaseSubAgent):
    """Subagente para generación de presentaciones HTML."""
    
    id = "slides_agent"
    name = "Slides Agent"
    description = "Diseñador visual de presentaciones profesionales"
    version = "2.2.0"
    domain_tools = ["generate_image"]
    system_prompt = SLIDES_SYSTEM_PROMPT
    
    # Rol y expertise
    role = "Diseñador Visual de Presentaciones"
    expertise = """Soy diseñador visual especializado en presentaciones de alto impacto.

Puedo ayudarte con:
- Elegir el estilo visual adecuado (corporativo, creativo, minimalista, tech)
- Definir la paleta de colores según el tema y audiencia
- Estructurar el flujo narrativo de las slides
- Decidir qué slides necesitan imágenes vs datos vs texto
- Optimizar el impacto visual de tu mensaje

Cuando me consultes, te daré recomendaciones de diseño antes de crear la presentación."""

    task_requirements = """## MODOS DE USO

### Modo Consulta (recomendado primero)
Envía: {"mode": "consult", "topic": "tema", "audience": "audiencia", "purpose": "objetivo"}
→ Te daré recomendaciones de diseño y estructura

### Modo Ejecución
Envía el outline JSON:
{
  "title": "Título",
  "slides": [
    {"title": "...", "type": "title|bullets|stats|quote|comparison", "badge": "...", "bullets": [...]}
  ],
  "generate_images": ["prompt 1", "prompt 2"]  // opcional
}

TIPOS: title, bullets (máx 5), stats, quote, comparison, image"""
    
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
        
        Soporta dos modos:
        - consult: Devuelve recomendaciones de diseño
        - execute: Genera la presentación HTML
        
        La respuesta incluye Brain Events para Open WebUI.
        """
        start_time = time.time()
        
        # Detectar modo consulta
        try:
            task_data = json.loads(task)
            if task_data.get("mode") == "consult":
                logger.info("📊 SlidesAgent consulting", topic=task_data.get("topic", "")[:50])
                return await self._handle_consult(task_data, llm_url, model, provider_type, api_key)
        except (json.JSONDecodeError, TypeError):
            pass  # No es JSON, proceder con ejecución normal
        
        logger.info("📊 SlidesAgent executing", task_length=len(task))
        
        response_parts = []
        generated_images = []
        
        try:
            # Thinking event
            response_parts.append(thinking_event(
                "Procesando solicitud de presentación...",
                status="start"
            ))
            
            # Parsear outline y extraer imágenes a generar
            outline = self._parse_outline(task)
            images_to_generate = self._extract_images_to_generate(task)
            
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
                f"Outline: {outline.title}\n- {len(outline.slides)} slides" + 
                (f"\n- {len(images_to_generate)} imágenes a generar" if images_to_generate else ""),
                status="complete"
            ))
            
            # Generar imágenes si se solicitaron
            if images_to_generate and api_key:
                response_parts.append(action_event(
                    action_type="image",
                    title=f"Generando {len(images_to_generate)} imágenes",
                    status="running"
                ))
                
                generated_images = await self._generate_images(
                    images_to_generate, api_key
                )
                
                response_parts.append(action_event(
                    action_type="image",
                    title=f"Generando {len(images_to_generate)} imágenes",
                    status="completed",
                    results_count=len(generated_images)
                ))
            
            # Action: generando slides
            response_parts.append(action_event(
                action_type="slides",
                title=f"Generando {len(outline.slides)} slides",
                status="running"
            ))
            
            # Generar HTML
            html = SLIDES_CSS
            for i, slide in enumerate(outline.slides):
                # Añadir imagen si hay disponible para esta slide
                slide_image = generated_images[i] if i < len(generated_images) else None
                html += generate_slide_html(slide, image_url=slide_image)
            
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
            summary = f"\n✅ **{outline.title}**\n📊 {slides_count} slides"
            if generated_images:
                summary += f"\n🖼️ {len(generated_images)} imágenes"
            response_parts.append(summary + "\n")
            
            return SubAgentResult(
                success=True,
                response="".join(response_parts),
                agent_id=self.id,
                agent_name=self.name,
                tools_used=["slides_generator"] + (["image_generator"] if generated_images else []),
                images=[{"url": url, "prompt": "Generated for slides"} for url in generated_images],
                data={
                    "html": html,
                    "slides_count": slides_count,
                    "title": outline.title,
                    "images_generated": len(generated_images)
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
    
    def _extract_images_to_generate(self, task: str) -> List[str]:
        """Extrae lista de imágenes a generar del outline."""
        try:
            data = json.loads(task)
            images = data.get("generate_images", [])
            # Asegurar que sea una lista
            if isinstance(images, list):
                return [str(img) for img in images if img]
            elif isinstance(images, bool):
                return []  # Si es True/False, ignorar
            elif isinstance(images, str):
                return [images]  # Si es un string, convertir a lista
            return []
        except:
            return []
    
    async def _generate_images(
        self,
        prompts: List[str],
        api_key: str
    ) -> List[str]:
        """Genera imágenes usando DALL-E."""
        from src.tools.core.media import generate_image
        
        urls = []
        for prompt in prompts[:3]:  # Máximo 3 imágenes
            try:
                result = await generate_image(
                    prompt=prompt,
                    provider="openai",
                    model="dall-e-3",
                    size="1024x1024",
                    _api_key=api_key
                )
                if result.get("success") and result.get("url"):
                    urls.append(result["url"])
                    logger.info(f"Generated image for slides: {prompt[:50]}...")
            except Exception as e:
                logger.warning(f"Could not generate image: {e}")
        
        return urls
    
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
    
    async def _handle_consult(
        self,
        task_data: Dict[str, Any],
        llm_url: Optional[str],
        model: Optional[str],
        provider_type: str,
        api_key: Optional[str]
    ) -> SubAgentResult:
        """
        Modo consulta: da recomendaciones de diseño antes de crear la presentación.
        """
        from ...llm_utils import call_llm_with_tools
        
        topic = task_data.get("topic", "")
        audience = task_data.get("audience", "general")
        purpose = task_data.get("purpose", "informar")
        context = task_data.get("context", "")
        
        consult_prompt = f"""Eres un Diseñador Visual de Presentaciones con experiencia en comunicación visual.

Un colega te pide ayuda para diseñar una presentación:

**TEMA:** {topic}
**AUDIENCIA:** {audience}
**OBJETIVO:** {purpose}
{f"**CONTEXTO:** {context}" if context else ""}

Dame tus recomendaciones de diseño de forma concisa y profesional:

1. **Estilo Visual** - ¿Qué estilo recomendarías? (corporativo, creativo, minimalista, tech-futurista, editorial, etc.)

2. **Paleta de Colores** - ¿Qué colores transmitirían mejor el mensaje?

3. **Estructura Narrativa** - ¿Cómo organizarías el flujo? (número de slides, tipos de contenido)

4. **Elementos Visuales** - ¿Necesita imágenes, iconos, estadísticas, comparaciones?

5. **Recomendación Principal** - Tu sugerencia estrella para que destaque

Sé conciso pero útil. Puedes hacer una pregunta al final si necesitas clarificar algo antes de diseñar."""

        try:
            if not llm_url or not api_key:
                # Respuesta por defecto sin LLM
                return SubAgentResult(
                    success=True,
                    response=f"""🎨 **Recomendaciones de Diseño para "{topic}"**

**Estilo Visual:** Te sugiero un estilo moderno y limpio que se adapte a tu audiencia ({audience}).

**Estructura Sugerida:**
1. Slide de título impactante
2. Contexto/Problema (por qué importa)
3-4. Puntos clave (bullets concisos)
5. Datos o comparación (si aplica)
6. Conclusión con call-to-action

**Elementos Visuales:** Dependiendo del tema, considera incluir imágenes o estadísticas para mayor impacto.

¿Quieres que proceda con este enfoque o tienes preferencias específicas?""",
                    agent_id=self.id,
                    agent_name=self.name,
                    data={"mode": "consult", "topic": topic, "ready_for_execution": True}
                )
            
            response = await call_llm_with_tools(
                messages=[
                    {"role": "system", "content": "Eres un diseñador visual experto. Responde de forma concisa y profesional en español."},
                    {"role": "user", "content": consult_prompt}
                ],
                tools=[],
                temperature=0.7,
                provider_type=provider_type,
                api_key=api_key,
                llm_url=llm_url,
                model=model
            )
            
            return SubAgentResult(
                success=True,
                response=response.content or "Sin recomendaciones",
                agent_id=self.id,
                agent_name=self.name,
                data={"mode": "consult", "topic": topic, "ready_for_execution": True}
            )
            
        except Exception as e:
            logger.error(f"Consult error: {e}")
            return SubAgentResult(
                success=False,
                response=f"Error en consulta: {str(e)}",
                agent_id=self.id,
                agent_name=self.name,
                error=str(e)
            )
