"""
Designer Agent - Subagente de diseño visual.

Fusiona capacidades de imágenes y presentaciones.
Usa LLM con tools para decidir qué generar según la tarea.
Sistema de Skills: carga conocimiento especializado según la tarea.
"""

import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

import structlog

from ..base import BaseSubAgent, SubAgentResult, Skill
from ..slides.themes import get_theme, generate_css, detect_theme_from_topic, create_custom_theme, THEMES
from ..slides.templates import SlideOutline, PresentationOutline, generate_slide_html
from ..slides.events import thinking_event, action_event, artifact_event

logger = structlog.get_logger()


def _read_system_prompt() -> str:
    """Lee el prompt desde fichero."""
    path = Path(__file__).parent / "prompts" / "system_prompt.txt"
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return "Eres un diseñador visual. Genera imágenes o presentaciones según la tarea."


# Skills disponibles para el Designer (el LLM decide cuándo cargar)
DESIGNER_SKILLS = [
    Skill(
        id="slides",
        name="Presentaciones Modernas",
        description="Layouts HTML/CSS avanzados, animaciones, templates profesionales para presentaciones"
    ),
    Skill(
        id="branding",
        name="Branding e Identidad",
        description="Prompts para logos, paletas de color, tipografías, identidad visual"
    ),
    Skill(
        id="data_viz",
        name="Visualización de Datos",
        description="Gráficos SVG, charts, infografías con código listo para usar"
    )
]


class DesignerAgent(BaseSubAgent):
    """Subagente de diseño: imágenes y presentaciones con sistema de skills."""

    id = "designer_agent"
    name = "Designer"
    description = "Diseñador visual: imágenes, presentaciones, logos"
    version = "2.0.0"  # Versión con skills
    domain_tools = ["generate_image", "generate_slides"]
    system_prompt = ""  # Se carga desde fichero
    available_skills = DESIGNER_SKILLS  # Skills disponibles

    role = "Diseñador Visual"
    expertise = """Soy diseñador visual. Creo imágenes (logos, ilustraciones, fotos) y presentaciones profesionales.
Puedo combinar ambos: presentaciones con imágenes generadas.
Tengo skills especializados en: slides modernas, branding, visualización de datos."""

    task_requirements = "Describe la tarea: imagen, presentación, o ambos. Puedes enviar texto libre o JSON con outline."

    def __init__(self):
        super().__init__()
        self.system_prompt = _read_system_prompt()
        logger.info(f"🎨 DesignerAgent initialized with {len(self.available_skills)} skills")

    async def execute(
        self,
        task: str,
        context: Optional[str] = None,
        llm_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_type: str = "ollama",
        api_key: Optional[str] = None
    ) -> SubAgentResult:
        """Ejecuta la tarea usando LLM con tools."""
        start_time = time.time()
        logger.info("🎨 DesignerAgent executing", task=task[:100])

        try:
            # Si ya viene outline JSON válido, generar presentación directo
            outline = self._parse_outline(task)
            if outline:
                return await self._generate_presentation(
                    outline, task, context, api_key, start_time
                )

            # Si es descripción corta de imagen, generar imagen directo
            if self._looks_like_image_request(task):
                return await self._generate_image(task, start_time)

            # Usar LLM para decidir
            if llm_url and model:
                return await self._execute_with_llm(
                    task, context, llm_url, model, provider_type, api_key, start_time
                )

            # Fallback: intentar presentación desde task como tema
            outline = await self._create_outline_from_task(
                task, context, llm_url, model, provider_type, api_key
            )
            return await self._generate_presentation(
                outline, task, context, api_key, start_time
            )

        except Exception as e:
            logger.error(f"DesignerAgent error: {e}", exc_info=True)
            return SubAgentResult(
                success=False,
                response=f"Error: {str(e)}",
                agent_id=self.id,
                agent_name=self.name,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

    def _looks_like_image_request(self, task: str) -> bool:
        """Detecta si parece solicitud de imagen."""
        t = task.lower().strip()
        if len(t) > 300:
            return False
        keywords = ["imagen", "logo", "dibujo", "ilustración", "foto", "picture", "image", "generate", "crea"]
        return any(k in t for k in keywords) and "presentación" not in t and "slides" not in t

    def _parse_outline(self, task: str) -> Optional[PresentationOutline]:
        """Parsea task como JSON outline."""
        try:
            data = json.loads(task)
            if not isinstance(data, dict) or "title" not in data:
                return None

            slides = []
            for s in data.get("slides", []):
                raw_bullets = s.get("bullets", [])
                if isinstance(raw_bullets, str):
                    try:
                        raw_bullets = json.loads(raw_bullets)
                    except Exception:
                        raw_bullets = [raw_bullets]
                if not isinstance(raw_bullets, list):
                    raw_bullets = []
                clean_bullets = [str(b).strip() for b in raw_bullets if b]

                slides.append(SlideOutline(
                    title=str(s.get("title", "")),
                    type=s.get("type", "content"),
                    content=s.get("content"),
                    badge=s.get("badge"),
                    bullets=clean_bullets,
                    stats=s.get("stats", []),
                    items=s.get("items", []),
                    quote=s.get("quote"),
                    author=s.get("author")
                ))

            images = data.get("generate_images", [])
            if isinstance(images, str):
                images = [images]
            images = [str(i) for i in images] if isinstance(images, list) else []

            return PresentationOutline(
                title=data["title"],
                slides=slides,
                theme=data.get("theme", "dark"),
                generate_images=images[:5],
                language=data.get("language", "es")
            )
        except (json.JSONDecodeError, TypeError):
            return None

    async def _generate_image(self, task: str, start_time: float) -> SubAgentResult:
        """Genera imagen."""
        from src.tools.domains.media import generate_image

        result = await generate_image(prompt=task)
        if result.get("success"):
            images = [{
                "url": result.get("image_url"),
                "prompt": result.get("prompt"),
                "provider": result.get("provider"),
                "model": result.get("model")
            }]
            response = f"He generado la imagen.\n\n![Imagen]({result.get('image_url', '')})"
            return SubAgentResult(
                success=True,
                response=response,
                agent_id=self.id,
                agent_name=self.name,
                tools_used=["generate_image"],
                images=images,
                data=result,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        return SubAgentResult(
            success=False,
            response=f"Error: {result.get('error', 'Unknown')}",
            agent_id=self.id,
            agent_name=self.name,
            error=result.get("error"),
            execution_time_ms=int((time.time() - start_time) * 1000)
        )

    async def _generate_presentation(
        self,
        outline: PresentationOutline,
        task: str,
        context: Optional[str],
        api_key: Optional[str],
        start_time: float
    ) -> SubAgentResult:
        """Genera presentación HTML."""
        response_parts = []
        generated_images = []

        # Imágenes a generar (del outline o del task)
        images_to_generate = list(outline.generate_images) if outline.generate_images else []
        if not images_to_generate:
            try:
                data = json.loads(task) if task.strip().startswith("{") else {}
                images_to_generate = data.get("generate_images", [])
                if isinstance(images_to_generate, str):
                    images_to_generate = [images_to_generate]
            except Exception:
                pass

        if images_to_generate:
            response_parts.append(action_event("image", "Generando imágenes", "running"))
            generated_images = await self._generate_images(images_to_generate[:3])
            response_parts.append(action_event("image", "Generando imágenes", "completed", len(generated_images)))

        response_parts.append(action_event("slides", f"Generando {len(outline.slides)} slides", "running"))

        theme, _ = self._extract_theme(task, outline)
        html = generate_css(theme)
        for i, slide in enumerate(outline.slides):
            img = generated_images[i] if i < len(generated_images) else None
            html += generate_slide_html(slide, image_url=img)

        slides_count = html.count('class="slide"')
        response_parts.append(artifact_event(html_content=html, title=outline.title))
        response_parts.append(action_event("slides", f"Generando {len(outline.slides)} slides", "completed"))

        summary = f"\n✅ **{outline.title}**\n📊 {slides_count} slides"
        if generated_images:
            summary += f"\n🖼️ {len(generated_images)} imágenes"
        response_parts.append(summary + "\n")

        return SubAgentResult(
            success=True,
            response="".join(response_parts),
            agent_id=self.id,
            agent_name=self.name,
            tools_used=["generate_slides"] + (["generate_image"] if generated_images else []),
            images=[{"url": u, "prompt": "For slides"} for u in generated_images],
            data={
                "html": html,
                "slides_count": slides_count,
                "title": outline.title,
                "images_generated": len(generated_images)
            },
            execution_time_ms=int((time.time() - start_time) * 1000)
        )

    def _extract_theme(self, task: str, outline: PresentationOutline):
        """Extrae tema del task o outline."""
        try:
            data = json.loads(task)
            if "colors" in data and isinstance(data["colors"], dict):
                return create_custom_theme(data["colors"], data.get("theme", "dark")), "custom"
            if "theme" in data and data["theme"] in THEMES:
                return get_theme(data["theme"]), data["theme"]
        except Exception:
            pass
        detected = detect_theme_from_topic(outline.title)
        return get_theme(detected), detected

    async def _generate_images(self, prompts: List[str]) -> List[str]:
        """Genera imágenes para slides (API key desde Strapi)."""
        from src.tools.domains.media.generate_image import generate_image

        urls = []
        for prompt in prompts[:3]:
            try:
                result = await generate_image(
                    prompt=str(prompt),
                    provider="openai",
                    model="dall-e-3",
                    size="1024x1024"
                )
                url = result.get("image_url") or result.get("url")
                if result.get("success") and url:
                    urls.append(url)
            except Exception as e:
                logger.warning(f"Image gen failed: {e}")
        return urls

    async def _create_outline_from_task(
        self,
        task: str,
        context: Optional[str],
        llm_url: Optional[str],
        model: Optional[str],
        provider_type: str,
        api_key: Optional[str]
    ) -> PresentationOutline:
        """Crea outline desde texto usando LLM."""
        from ...llm_utils import call_llm

        if not llm_url or not model:
            return PresentationOutline(
                title="Presentación",
                slides=[
                    SlideOutline(title="Introducción", type="title", badge="INICIO"),
                    SlideOutline(title="Contenido", type="content", content=task[:300])
                ]
            )

        # Usar skill si ya fue cargado previamente (por el LLM en _execute_with_llm)
        skill_context = ""
        if "slides" in self._skills_cache:
            skill_context = """
LAYOUTS DISPONIBLES:
- slide-title: Portada y títulos de sección
- slide-split: Contenido + imagen lado a lado
- slide-cards: Grid de cards (servicios, features)
- slide-stats: Números grandes y métricas
- slide-quote: Testimonios y citas
- slide-timeline: Evolución temporal

Incluye "layout" en cada slide."""

        prompt = f"""Crea una presentación profesional como JSON.

TEMA: {task}
{f"CONTEXTO: {context}" if context else ""}
{skill_context}

Formato JSON:
{{
  "title": "Título de la Presentación",
  "theme": "dark",
  "slides": [
    {{"title": "...", "type": "title", "layout": "slide-title", "badge": "SECCIÓN"}},
    {{"title": "...", "type": "bullets", "layout": "slide-split", "bullets": ["...", "..."]}},
    {{"title": "...", "type": "stats", "layout": "slide-stats", "stats": [{{"value": "98%", "label": "..."}}]}},
    {{"title": "...", "type": "cards", "layout": "slide-cards", "items": [{{"icon": "🚀", "title": "...", "text": "..."}}]}}
  ],
  "generate_images": ["prompt imagen 1 en inglés", "prompt imagen 2 en inglés"]
}}

REGLAS:
1. generate_images: SIEMPRE incluye 1-3 prompts en inglés para imágenes (ej: "Modern abstract illustration of [concept], gradient blue purple, minimalist")
2. Varía los layouts: no uses el mismo tipo de slide consecutivamente
3. Usa stats para métricas y KPIs, cards para listar servicios/features
4. Máximo 5-7 slides, menos es más
5. Responde SOLO con JSON válido, sin texto adicional."""

        response = await call_llm(
            llm_url=llm_url,
            model=model,
            messages=[
                {"role": "system", "content": "Eres un experto en presentaciones. Responde SOLO con JSON válido."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            provider_type=provider_type,
            api_key=api_key
        )

        response = response.strip()
        for prefix in ["```json", "```"]:
            if response.startswith(prefix):
                response = response[len(prefix):]
        if response.endswith("```"):
            response = response[:-3]

        outline = self._parse_outline(response)
        if not outline:
            return PresentationOutline(
                title="Presentación",
                slides=[
                    SlideOutline(title="Introducción", type="title", badge="INICIO"),
                    SlideOutline(title="Contenido", type="content", content=task[:300])
                ]
            )
        return outline

    async def _execute_with_llm(
        self,
        task: str,
        context: Optional[str],
        llm_url: str,
        model: str,
        provider_type: str,
        api_key: Optional[str],
        start_time: float
    ) -> SubAgentResult:
        """Ejecuta con LLM que decide si cargar skills y qué herramienta usar."""
        from ...llm_utils import call_llm_with_tools

        # Tools de ejecución
        execution_tools = [
            {
                "type": "function",
                "function": {
                    "name": "generate_image",
                    "description": "Genera una imagen con IA",
                    "parameters": {
                        "type": "object",
                        "properties": {"prompt": {"type": "string", "description": "Descripción de la imagen"}},
                        "required": ["prompt"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_presentation",
                    "description": "Genera presentación HTML. outline es JSON con title, slides y generate_images.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "outline": {"type": "string", "description": "JSON con title, slides array y generate_images"},
                            "context": {"type": "string", "description": "Contexto adicional"}
                        },
                        "required": ["outline"]
                    }
                }
            }
        ]

        # Añadir tool de skills si hay disponibles
        load_skill_tool = self.get_load_skill_tool()
        tools = [load_skill_tool] + execution_tools if load_skill_tool else execution_tools

        # Prompt con info de skills disponibles
        system_prompt = self.system_prompt + self.get_skills_for_prompt()
        
        user_content = f"Tarea: {task}"
        if context:
            user_content += f"\n\nContexto: {context}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        # Loop: el LLM puede cargar skills antes de ejecutar
        max_iterations = 3
        
        for iteration in range(max_iterations):
            response = await call_llm_with_tools(
                messages=messages,
                tools=tools,
                temperature=0.5,
                provider_type=provider_type,
                api_key=api_key,
                llm_url=llm_url,
                model=model
            )

            if not response.tool_calls:
                # Sin tool call: fallback a presentación
                break
            
            for tc in response.tool_calls:
                name = tc.function.get("name", "")
                args = json.loads(tc.function.get("arguments", "{}"))

                # Tool: load_skill - carga conocimiento y continúa
                if name == "load_skill":
                    skill_id = args.get("skill_id", "")
                    result = self.load_skill(skill_id)
                    
                    if result.get("success"):
                        # Añadir skill al contexto y continuar el loop
                        skill_content = result.get("content", "")
                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{"id": tc.id, "type": "function", "function": tc.function}]
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": f"Skill '{skill_id}' cargado. Contenido:\n\n{skill_content}"
                        })
                        logger.info(f"🎯 LLM loaded skill: {skill_id}")
                        continue  # Siguiente iteración para que el LLM use el skill
                    else:
                        # Error cargando skill
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": f"Error: {result.get('error')}"
                        })
                        continue

                # Tool: generate_image - ejecutar y retornar
                elif name == "generate_image":
                    return await self._generate_image(
                        args.get("prompt", task),
                        start_time
                    )
                
                # Tool: generate_presentation - ejecutar y retornar
                elif name == "generate_presentation":
                    outline_str = args.get("outline", "{}")
                    outline = self._parse_outline(outline_str)
                    if not outline:
                        outline = await self._create_outline_from_task(
                            outline_str or task,
                            args.get("context") or context,
                            llm_url, model, provider_type, api_key
                        )
                    return await self._generate_presentation(
                        outline, outline_str, context, api_key, start_time
                    )

        # Fallback: intentar presentación sin skill
        outline = await self._create_outline_from_task(
            task, context, llm_url, model, provider_type, api_key
        )
        return await self._generate_presentation(
            outline, task, context, api_key, start_time
        )
