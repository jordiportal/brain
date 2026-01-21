"""
Browser Agent - REFACTORIZADO con estándar
Agente que puede navegar por internet usando Playwright.

Implementa bucle ReAct (Reason-Act):
1. Observa el estado actual (página, elementos)
2. Razona sobre qué acción tomar
3. Ejecuta la acción usando el servicio de navegación
4. Repite hasta completar la tarea
"""

import json
from typing import AsyncGenerator, Optional, List, Dict, Any
import structlog

from ..models import (
    ChainDefinition,
    ChainConfig,
    NodeDefinition,
    NodeType,
    StreamEvent
)
from ..registry import chain_registry
from .llm_utils import call_llm_stream
from ...browser.service import browser_service
from .agent_helpers import extract_json  # ✅ Usar helper compartido

logger = structlog.get_logger()


# ============================================
# Funciones específicas del Browser Agent
# ============================================

async def execute_browser_action(action: str, arguments: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Ejecutar una acción del navegador via browser_service"""
    try:
        if action == "browser_navigate":
            return await browser_service.navigate(
                url=arguments.get("url", ""),
                session_id=session_id
            )
        elif action == "browser_get_content":
            return await browser_service.get_content(
                session_id=session_id,
                selector=arguments.get("selector", "body")
            )
        elif action == "browser_screenshot":
            return await browser_service.screenshot(
                session_id=session_id,
                full_page=arguments.get("full_page", False)
            )
        elif action == "browser_click":
            return await browser_service.click(
                selector=arguments.get("selector", ""),
                session_id=session_id
            )
        elif action == "browser_type":
            return await browser_service.type_text(
                selector=arguments.get("selector", ""),
                text=arguments.get("text", ""),
                session_id=session_id,
                press_enter=arguments.get("press_enter", False)
            )
        elif action == "browser_get_elements":
            return await browser_service.get_elements(
                session_id=session_id,
                limit=arguments.get("limit", 50)
            )
        elif action == "browser_scroll":
            return await browser_service.scroll(
                direction=arguments.get("direction", "down"),
                amount=arguments.get("amount", 500),
                session_id=session_id
            )
        else:
            return {"success": False, "error": f"Acción desconocida: {action}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def format_browser_result(action: str, result: Dict[str, Any]) -> str:
    """Formatear resultado de acción del navegador para mostrar"""
    if not result.get("success"):
        return f"❌ Error: {result.get('error', 'Error desconocido')}"
    
    if action == "browser_screenshot":
        return f"📸 Captura tomada (URL: {result.get('url', '')})"
    elif action == "browser_get_content":
        text = result.get("text", "")[:1000]
        return f"📄 Contenido:\n{text}{'...' if result.get('truncated') else ''}"
    elif action == "browser_get_elements":
        elements = result.get("elements", [])[:25]
        result_text = "🔍 Elementos encontrados:\n"
        for el in elements:
            el_info = f"[{el.get('tag')}]"
            if el.get('id'):
                el_info += f" id='{el.get('id')}'"
            if el.get('text'):
                el_info += f" '{el.get('text')[:40]}'"
            elif el.get('placeholder'):
                el_info += f" placeholder='{el.get('placeholder')[:30]}'"
            elif el.get('aria-label'):
                el_info += f" aria-label='{el.get('aria-label')[:30]}'"
            if el.get('frame') == 'iframe':
                el_info += " (iframe)"
            result_text += f"- {el_info}\n"
        return result_text
    elif action == "browser_scroll":
        return f"📜 Scroll {result.get('direction')} - Posición: {result.get('scroll_position')}/{result.get('page_height')}px"
    else:
        return f"✅ {json.dumps(result, ensure_ascii=False)[:500]}"


# ============================================
# Definición del Agente (con prompts editables)
# ============================================

BROWSER_AGENT_DEFINITION = ChainDefinition(
    id="browser_agent",
    name="Browser Agent",
    description="Agente inteligente que puede navegar por internet usando un navegador Chrome. Puede buscar información, interactuar con páginas web, llenar formularios y extraer datos.",
    type="agent",
    version="2.0.0",  # ✅ Versión actualizada
    nodes=[
        NodeDefinition(
            id="input",
            type=NodeType.INPUT,
            name="Tarea de navegación"
        ),
        NodeDefinition(
            id="browser_init",
            type=NodeType.TOOL,
            name="Inicialización"
        ),
        NodeDefinition(
            id="react_loop",
            type=NodeType.LLM,
            name="Bucle ReAct",
            # ✅ System prompt editable
            system_prompt="""Eres un agente inteligente que puede navegar por internet usando un navegador Chrome.

## HERRAMIENTAS DISPONIBLES

1. **browser_navigate** - Navegar a una URL
   - Argumentos: {"url": "https://example.com"}

2. **browser_get_content** - Obtener el texto de la página actual
   - Argumentos: {} o {"selector": "main"}

3. **browser_screenshot** - Tomar captura de pantalla
   - Argumentos: {"full_page": true} o {}

4. **browser_click** - Hacer clic en un elemento
   - Argumentos: {"selector": "button.submit"}

5. **browser_type** - Escribir texto en un campo
   - Argumentos: {"selector": "input[name='q']", "text": "búsqueda", "press_enter": true}

6. **browser_get_elements** - Ver elementos interactivos de la página
   - Argumentos: {}

7. **browser_scroll** - Hacer scroll para ver más contenido
   - Argumentos: {"direction": "down", "amount": 500}
   - Direcciones: "down", "up", "top", "bottom"

## FORMATO DE RESPUESTA
SIEMPRE responde con este formato JSON cuando necesites usar una herramienta:
```json
{
    "thinking": "Tu razonamiento sobre qué hacer",
    "action": "nombre_de_la_herramienta",
    "arguments": {
        "param1": "valor1"
    }
}
```

Si ya tienes suficiente información para responder al usuario, usa:
```json
{
    "thinking": "Razonamiento final",
    "action": "FINAL_ANSWER",
    "answer": "Tu respuesta completa al usuario"
}
```

## SELECTORES CSS COMUNES
- `input[type="text"]` o `input[name="q"]` - Campos de texto
- `button` o `button[type="submit"]` - Botones
- `a` o `a[href*="example"]` - Enlaces
- `.clase` - Por clase CSS
- `#id` - Por ID

## INSTRUCCIONES
1. Analiza la tarea del usuario.
2. Navega a la página necesaria con browser_navigate.
3. Usa browser_get_elements para ver qué elementos hay.
4. **MANEJO DE COOKIES/POPUPS:** Si ves un diálogo de cookies o privacidad (botones como "Aceptar", "Acepto", "Agree", "Consent"), DEBES hacer clic en él antes de continuar.
5. Interactúa usando browser_click o browser_type. Si un clic no funciona, busca el elemento de nuevo.
6. Si necesitas ver más contenido, usa browser_scroll.
7. Usa browser_get_content para leer información.
8. Cuando tengas la información, da FINAL_ANSWER.

## EJEMPLO DE FLUJO
Usuario: "Busca en Google información sobre Python"

1. browser_navigate → {"url": "https://www.google.com"}
2. browser_get_elements → ver elementos disponibles
3. browser_type → {"selector": "input[name='q']", "text": "Python", "press_enter": true}
4. browser_scroll → {"direction": "down"} (si necesitas ver más)
5. browser_get_content → leer resultados
6. FINAL_ANSWER → resumir los resultados""",
            temperature=0.2
        ),
        NodeDefinition(
            id="synthesizer",
            type=NodeType.LLM,
            name="Sintetizador",
            # ✅ System prompt editable
            system_prompt="""Eres un asistente que resume los resultados de una navegación web. Genera una respuesta clara y útil basada en la información recopilada.

TAREA ORIGINAL: {{user_query}}

INFORMACIÓN RECOPILADA:
{{observations_summary}}

Genera una respuesta completa y útil para el usuario.""",
            prompt_template="Genera la respuesta final.",
            temperature=0.5
        ),
        NodeDefinition(
            id="output",
            type=NodeType.OUTPUT,
            name="Respuesta"
        )
    ],
    config=ChainConfig(
        temperature=0.2,
        use_memory=True,
        max_tokens=4096
    )
)


# ============================================
# Builder Function (Lógica del Agente)
# ============================================

async def build_browser_agent(
    config: ChainConfig,
    llm_url: str,
    model: str,
    input_data: dict,
    memory: list = None,
    execution_state: dict = None,
    execution_id: str = "",
    stream: bool = True,
    llm_provider_type: str = "ollama",
    llm_api_key: Optional[str] = None,
    **kwargs
) -> AsyncGenerator[StreamEvent, None]:
    """
    Builder del agente de navegación web.
    
    FASES:
    1. Initialization: Inicializar navegador Playwright
    2. ReAct Loop: Bucle Reason-Act (máx 15 pasos)
       - Reason: LLM decide acción
       - Act: Ejecutar acción del navegador
       - Observe: Ver resultado
    3. Synthesis: Resumir resultados finales
    4. Cleanup: Cerrar sesión de navegador
    
    NODOS:
    - input (INPUT): Tarea de navegación
    - browser_init (TOOL): Inicializar Playwright
    - react_loop (LLM): Bucle ReAct con herramientas browser
    - synthesizer (LLM): Resumir resultados
    - output (OUTPUT): Respuesta final
    
    MEMORY: Yes (conversación)
    TOOLS: Browser (navigate, click, type, get_content, screenshot, scroll, get_elements)
    """
    
    query = input_data.get("message", input_data.get("query", ""))
    max_steps = input_data.get("max_steps", 15)
    session_id = execution_id or "default"
    
    if not query:
        yield StreamEvent(
            event_type="error",
            execution_id=execution_id,
            data={"error": "No se proporcionó una tarea"}
        )
        return
    
    # ✅ Obtener nodos con prompts editables
    react_node = BROWSER_AGENT_DEFINITION.get_node("react_loop")
    synth_node = BROWSER_AGENT_DEFINITION.get_node("synthesizer")
    
    if not all([react_node, synth_node]):
        raise ValueError("Nodos del Browser Agent no encontrados")
    
    # ========== FASE 1: INITIALIZATION ==========
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="browser_init",
        node_name="🌐 Iniciando navegador",
        data={}
    )
    
    initialized = await browser_service.initialize()
    if not initialized:
        yield StreamEvent(
            event_type="token",
            execution_id=execution_id,
            node_id="browser_init",
            content="❌ No se pudo inicializar el navegador. Verifica que Playwright esté instalado."
        )
        yield StreamEvent(
            event_type="node_end",
            execution_id=execution_id,
            node_id="browser_init",
            node_name="🌐 Iniciando navegador",
            data={"error": "Playwright no disponible"}
        )
        return
    
    yield StreamEvent(
        event_type="token",
        execution_id=execution_id,
        node_id="browser_init",
        content="✅ Navegador Chrome iniciado correctamente"
    )
    
    yield StreamEvent(
        event_type="node_end",
        execution_id=execution_id,
        node_id="browser_init",
        node_name="🌐 Iniciando navegador",
        data={"status": "ready"}
    )
    
    # ========== FASE 2: REACT LOOP ==========
    observations: List[Dict[str, Any]] = []
    final_answer = None
    
    for step in range(1, max_steps + 1):
        yield StreamEvent(
            event_type="node_start",
            execution_id=execution_id,
            node_id=f"step_{step}",
            node_name=f"🤔 Paso {step}: Razonando",
            data={"step": step}
        )
        
        # Construir mensajes para el LLM
        messages = [{"role": "system", "content": react_node.system_prompt}]
        
        # Agregar la tarea del usuario con historial
        user_message = f"**TAREA:** {query}"
        if observations:
            user_message += "\n\n**HISTORIAL DE ACCIONES:**\n"
            for obs in observations[-5:]:
                user_message += f"\n---\n**Acción:** {obs.get('action')}\n**Resultado:** {str(obs.get('result', ''))[:1500]}"
        
        messages.append({"role": "user", "content": user_message})
        
        # Llamar al LLM
        reasoning = ""
        async for token in call_llm_stream(
            llm_url, model, messages,
            temperature=react_node.temperature,
            provider_type=llm_provider_type,
            api_key=llm_api_key
        ):
            reasoning += token
            yield StreamEvent(
                event_type="token",
                execution_id=execution_id,
                node_id=f"step_{step}",
                content=token
            )
        
        # ✅ Extraer la acción usando helper compartido
        action_data = extract_json(reasoning)
        
        yield StreamEvent(
            event_type="node_end",
            execution_id=execution_id,
            node_id=f"step_{step}",
            node_name=f"🤔 Paso {step}: Razonando",
            data={"action": action_data.get("action") if action_data else None}
        )
        
        if not action_data:
            observations.append({
                "action": "parse_error",
                "result": "No se pudo extraer una acción válida de la respuesta"
            })
            continue
        
        action = action_data.get("action", "")
        
        # Verificar si es respuesta final
        if action == "FINAL_ANSWER":
            final_answer = action_data.get("answer", reasoning)
            break
        
        # Ejecutar la acción del navegador
        arguments = action_data.get("arguments", {})
        
        yield StreamEvent(
            event_type="node_start",
            execution_id=execution_id,
            node_id=f"action_{step}",
            node_name=f"🖱️ {action}",
            data={"tool": action, "arguments": arguments}
        )
        
        result = await execute_browser_action(action, arguments, session_id)
        result_text = format_browser_result(action, result)
        
        yield StreamEvent(
            event_type="token",
            execution_id=execution_id,
            node_id=f"action_{step}",
            content=f"**Resultado:**\n```\n{result_text}\n```"
        )
        
        observations.append({
            "action": action,
            "arguments": arguments,
            "result": result
        })
        
        yield StreamEvent(
            event_type="node_end",
            execution_id=execution_id,
            node_id=f"action_{step}",
            node_name=f"🖱️ {action}",
            data={"success": result.get("success", False)}
        )
    
    # ========== FASE 3: SYNTHESIS ==========
    if not final_answer:
        yield StreamEvent(
            event_type="node_start",
            execution_id=execution_id,
            node_id="final_synthesis",
            node_name="📝 Sintetizando respuesta",
            data={}
        )
        
        # Preparar resumen de observaciones
        obs_summary = []
        for obs in observations[-10:]:
            result = obs.get("result", {})
            if isinstance(result, dict):
                if result.get("text"):
                    obs_summary.append(f"Contenido: {result['text'][:500]}")
                elif result.get("elements"):
                    obs_summary.append(f"Elementos: {len(result['elements'])} encontrados")
                else:
                    obs_summary.append(f"{obs['action']}: {str(result)[:200]}")
            else:
                obs_summary.append(f"{obs['action']}: {str(result)[:200]}")
        
        # ✅ Reemplazar variables en synthesizer prompt
        synth_prompt = synth_node.system_prompt
        synth_prompt = synth_prompt.replace("{{user_query}}", query)
        synth_prompt = synth_prompt.replace("{{observations_summary}}", "\n".join(obs_summary))
        
        synth_messages = [
            {"role": "system", "content": synth_prompt},
            {"role": "user", "content": synth_node.prompt_template}
        ]
        
        final_answer = ""
        async for token in call_llm_stream(
            llm_url, model, synth_messages,
            temperature=synth_node.temperature,
            provider_type=llm_provider_type,
            api_key=llm_api_key
        ):
            final_answer += token
            yield StreamEvent(
                event_type="token",
                execution_id=execution_id,
                node_id="final_synthesis",
                content=token
            )
        
        yield StreamEvent(
            event_type="node_end",
            execution_id=execution_id,
            node_id="final_synthesis",
            node_name="📝 Sintetizando respuesta",
            data={}
        )
    
    # ========== FASE 4: CLEANUP ==========
    await browser_service.close_session(session_id)
    
    # Evento final
    yield StreamEvent(
        event_type="final",
        execution_id=execution_id,
        node_id="output",
        content=final_answer,
        data={
            "steps": len(observations),
            "final_answer": final_answer
        }
    )


# ============================================
# Registro del Agente
# ============================================

def register_browser_agent():
    """Registrar el agente de navegación en el registry"""
    
    chain_registry.register(
        chain_id="browser_agent",
        definition=BROWSER_AGENT_DEFINITION,
        builder=build_browser_agent
    )
    
    logger.info("Browser Agent registrado (v2.0.0)")
