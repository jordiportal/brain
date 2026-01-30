"""
Slides Chain - Cadena para generación de presentaciones

Esta cadena:
1. Analiza la solicitud del usuario
2. Busca información si es necesario (web search)
3. Crea un outline estructurado
4. Delega al SlidesAgent para generar el HTML
5. Emite Brain Events para Open WebUI

Modelo: brain-slides
"""

import json
import time
from typing import Dict, Any, Optional, List, AsyncGenerator

import structlog

from ..models import StreamEvent
from .agents.slides_agent import SlidesAgent, create_brain_event, create_thinking_event, create_action_event, create_sources_event, create_artifact_event

logger = structlog.get_logger()


async def slides_chain(
    config: Dict[str, Any],
    llm_url: str,
    model: str,
    input_data: Dict[str, Any],
    memory: Optional[List[Dict[str, str]]] = None,
    execution_id: Optional[str] = None,
    stream: bool = True,
    provider_type: str = "ollama",
    api_key: Optional[str] = None
) -> AsyncGenerator[StreamEvent, None]:
    """
    Cadena para generación de presentaciones.
    
    Flujo:
    1. Thinking: Analizar solicitud
    2. Action (search): Si necesita investigar
    3. Sources: Fuentes consultadas
    4. Action (slides): Generar slides
    5. Artifact: HTML de slides (progresivo)
    
    Args:
        config: Configuración de la cadena
        llm_url: URL del LLM backend
        model: Modelo a usar
        input_data: {"message": "Crea presentación sobre X", "query": "..."}
        memory: Historial de mensajes
        execution_id: ID de ejecución
        stream: Si hacer streaming
        provider_type: Tipo de proveedor
        api_key: API key
    """
    
    start_time = time.time()
    message = input_data.get("message") or input_data.get("query", "")
    
    logger.info(
        "📊 Slides chain started",
        execution_id=execution_id,
        message_length=len(message)
    )
    
    # Emit start event
    yield StreamEvent(
        event_type="start",
        execution_id=execution_id,
        data={
            "chain_id": "brain-slides",
            "chain_name": "Brain Slides Generator"
        }
    )
    
    slides_agent = SlidesAgent()
    sources_collected = []
    
    try:
        # PASO 1: Thinking - Analizar solicitud
        yield StreamEvent(
            event_type="token",
            execution_id=execution_id,
            content=create_thinking_event(
                f"Analizando solicitud de presentación...\n\nTema: {message[:100]}...",
                status="start"
            )
        )
        
        # Determinar si necesita búsqueda
        needs_search = _needs_web_search(message, config)
        
        if needs_search:
            # PASO 2: Action - Búsqueda web
            yield StreamEvent(
                event_type="token",
                execution_id=execution_id,
                content=create_action_event(
                    action_type="search",
                    title="Investigando el tema",
                    status="running"
                )
            )
            
            # Ejecutar búsqueda
            search_results, sources = await _search_topic(
                message,
                llm_url=llm_url,
                model=model,
                provider_type=provider_type,
                api_key=api_key
            )
            
            sources_collected = sources
            
            yield StreamEvent(
                event_type="token",
                execution_id=execution_id,
                content=create_action_event(
                    action_type="search",
                    title="Investigando el tema",
                    status="completed",
                    results_count=len(sources)
                )
            )
            
            # PASO 3: Sources
            if sources:
                yield StreamEvent(
                    event_type="token",
                    execution_id=execution_id,
                    content=create_sources_event(sources)
                )
        
        # PASO 4: Crear outline
        yield StreamEvent(
            event_type="token",
            execution_id=execution_id,
            content=create_thinking_event(
                "Estructurando la presentación...\n"
                "- Identificando puntos clave\n"
                "- Organizando el flujo narrativo\n"
                "- Seleccionando tipos de slides"
            )
        )
        
        outline = await _create_presentation_outline(
            topic=message,
            search_context=search_results if needs_search else None,
            llm_url=llm_url,
            model=model,
            provider_type=provider_type,
            api_key=api_key
        )
        
        yield StreamEvent(
            event_type="token",
            execution_id=execution_id,
            content=create_thinking_event(
                f"Outline creado: {outline.get('title', 'Presentación')}\n"
                f"- {len(outline.get('slides', []))} slides planificadas",
                status="complete"
            )
        )
        
        # PASO 5: Generar slides con el agente
        async for event in slides_agent.stream_execute(
            task=json.dumps(outline),
            context=search_results if needs_search else None,
            llm_url=llm_url,
            model=model,
            provider_type=provider_type,
            api_key=api_key,
            sources=sources_collected
        ):
            # El agente emite strings con Brain Events
            yield StreamEvent(
                event_type="token",
                execution_id=execution_id,
                content=event
            )
        
        # Finalizar
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        yield StreamEvent(
            event_type="end",
            execution_id=execution_id,
            data={
                "output": {"response": "Presentación generada"},
                "elapsed_ms": elapsed_ms
            }
        )
        
        logger.info(
            "✅ Slides chain completed",
            execution_id=execution_id,
            elapsed_ms=elapsed_ms
        )
        
    except Exception as e:
        logger.error(f"Slides chain error: {e}", exc_info=True)
        
        yield StreamEvent(
            event_type="token",
            execution_id=execution_id,
            content=f"\n❌ Error generando presentación: {str(e)}\n"
        )
        
        yield StreamEvent(
            event_type="error",
            execution_id=execution_id,
            data={"error": str(e)}
        )


def _needs_web_search(message: str, config: Any) -> bool:
    """Determina si la presentación necesita búsqueda web."""
    # Palabras que sugieren necesidad de datos actualizados
    research_keywords = [
        "actual", "reciente", "2024", "2025", "2026",
        "estadísticas", "datos", "tendencias",
        "comparativa", "mercado", "industria",
        "últimos", "novedades"
    ]
    
    message_lower = message.lower()
    
    # Si el config lo desactiva (soporta dict y objeto)
    if hasattr(config, 'web_search_enabled'):
        if not config.web_search_enabled:
            return False
    elif isinstance(config, dict) and not config.get("web_search_enabled", True):
        return False
    
    # Si contiene keywords de investigación
    return any(kw in message_lower for kw in research_keywords)


async def _search_topic(
    topic: str,
    llm_url: str,
    model: str,
    provider_type: str,
    api_key: Optional[str]
) -> tuple:
    """
    Busca información sobre el tema.
    
    Returns:
        (search_context: str, sources: List[Dict])
    """
    try:
        from ..chains.native_web_search import native_web_search_chain
        
        # Crear query de búsqueda
        search_query = f"{topic} información datos estadísticas"
        
        search_context = ""
        sources = []
        
        async for event in native_web_search_chain(
            config={},
            llm_url=llm_url,
            model=model,
            input_data={"message": search_query, "query": search_query},
            provider_type=provider_type,
            api_key=api_key
        ):
            if hasattr(event, 'event_type'):
                if event.event_type == "response_complete" and event.content:
                    search_context = event.content
                elif event.event_type == "sources" and event.data:
                    sources = event.data.get("sources", [])
        
        # Formatear sources para Brain Events
        formatted_sources = []
        for s in sources[:5]:  # Máximo 5 fuentes
            formatted_sources.append({
                "url": s.get("url", ""),
                "title": s.get("title", "Fuente"),
                "snippet": s.get("snippet", "")[:200],
                "favicon": "🌐"
            })
        
        return search_context, formatted_sources
        
    except Exception as e:
        logger.warning(f"Search failed: {e}")
        return "", []


async def _create_presentation_outline(
    topic: str,
    search_context: Optional[str],
    llm_url: str,
    model: str,
    provider_type: str,
    api_key: Optional[str]
) -> Dict[str, Any]:
    """Crea el outline estructurado de la presentación."""
    from .llm_utils import call_llm
    
    context_part = ""
    if search_context:
        context_part = f"""
INFORMACIÓN RECOPILADA:
{search_context[:2000]}
"""
    
    prompt = f"""Crea un outline de presentación como JSON para el siguiente tema.

TEMA: {topic}
{context_part}

Genera un JSON con esta estructura:
{{
  "title": "Título de la Presentación",
  "slides": [
    {{"title": "Introducción", "type": "title", "content": "Subtítulo", "badge": "INICIO"}},
    {{"title": "Contexto", "type": "content", "content": "Descripción del contexto", "badge": "CONTEXTO"}},
    {{"title": "Puntos Clave", "type": "bullets", "bullets": ["Punto 1", "Punto 2", "Punto 3"]}},
    {{"title": "Datos", "type": "stats", "stats": [{{"value": "85%", "label": "Métrica 1"}}, {{"value": "10x", "label": "Métrica 2"}}]}},
    {{"title": "Comparativa", "type": "comparison", "items": [{{"title": "Opción A", "description": "Descripción A"}}, {{"title": "Opción B", "description": "Descripción B"}}]}},
    {{"title": "Conclusiones", "type": "bullets", "bullets": ["Conclusión 1", "Conclusión 2"], "badge": "RESUMEN"}}
  ]
}}

REGLAS:
- Usa 5-8 slides
- Varía los tipos: title, content, bullets, stats, comparison
- Incluye badges descriptivos: INICIO, CONTEXTO, DATOS, ANÁLISIS, RESUMEN, etc.
- Contenido conciso pero informativo
- Si hay datos numéricos, usa slides tipo stats

Responde SOLO con JSON válido, sin explicaciones."""

    messages = [
        {"role": "system", "content": "Eres un experto en crear presentaciones estructuradas. Responde solo con JSON válido."},
        {"role": "user", "content": prompt}
    ]
    
    try:
        response = await call_llm(
            llm_url=llm_url,
            model=model,
            messages=messages,
            temperature=0.5,
            provider_type=provider_type,
            api_key=api_key
        )
        
        # Limpiar respuesta
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        outline = json.loads(response)
        
        # Validar estructura mínima
        if "title" not in outline:
            outline["title"] = topic[:50]
        if "slides" not in outline or not outline["slides"]:
            outline["slides"] = [
                {"title": topic[:50], "type": "title", "badge": "PRESENTACIÓN"}
            ]
        
        return outline
        
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Outline creation failed: {e}")
        
        # Fallback: outline básico
        return {
            "title": topic[:50] if len(topic) > 50 else topic,
            "slides": [
                {"title": topic[:50], "type": "title", "content": "Presentación generada", "badge": "INICIO"},
                {"title": "Contenido", "type": "content", "content": topic[:200]},
                {"title": "Conclusiones", "type": "bullets", "bullets": ["Punto clave 1", "Punto clave 2"], "badge": "RESUMEN"}
            ]
        }


# Registrar la cadena
def register_slides_chain():
    """Registra la cadena de slides en el registry."""
    from ..registry import chain_registry
    from ..models import ChainDefinition, ChainConfig
    
    definition = ChainDefinition(
        id="brain-slides",
        name="Brain Slides Generator",
        description="Genera presentaciones profesionales en HTML",
        type="custom",
        config=ChainConfig(
            temperature=0.7,
            max_tokens=4000
        )
    )
    
    chain_registry.register(
        chain_id="brain-slides",
        definition=definition,
        builder=slides_chain
    )
    logger.info("✅ brain-slides chain registered")
