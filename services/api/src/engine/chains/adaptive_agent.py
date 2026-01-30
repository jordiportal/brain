"""
Brain 2.0 Adaptive Agent - Agente principal con razonamiento adaptativo

Este es el ÚNICO agente de Brain 2.0. Usa las 15 core tools y ajusta
su modo de razonamiento según la complejidad de la tarea.

Flujo:
1. Analizar query → Detectar complejidad
2. Seleccionar modo de razonamiento (NONE, INTERNAL, EXTENDED)
3. Loop de ejecución con tools
4. Respuesta final via tool "finish"
"""

import json
from typing import AsyncGenerator, Optional, List, Dict, Any
from datetime import datetime

from ..models import (
    ChainDefinition,
    ChainConfig,
    NodeDefinition,
    NodeType,
    StreamEvent
)
from ..registry import chain_registry
from ..reasoning import (
    detect_complexity,
    get_reasoning_config,
    ComplexityLevel,
    ReasoningMode
)
from ...tools import tool_registry
from .llm_utils import call_llm_with_tools, LLMToolResponse, ToolCall

import structlog

logger = structlog.get_logger()


# ============================================
# Validación de Tool Names
# ============================================

# Lista de tools válidas
VALID_TOOL_NAMES = {
    "read_file", "write_file", "edit_file", "list_directory", "search_files",
    "shell", "python", "javascript",
    "web_search", "web_fetch",
    "think", "reflect", "plan", "finish",
    "calculate",
    "delegate",  # Para subagentes especializados
    "generate_slides"  # Generación de presentaciones con streaming
}

def is_valid_tool_name(name: str) -> bool:
    """
    Validar que el nombre de la tool es válido.
    Filtra artifacts de modelos como 'assistant<|channel|>commentary'
    """
    if not name:
        return False
    
    # Patrones inválidos (artifacts de modelos)
    invalid_patterns = ['<|', '|>', 'channel', 'functions<', 'assistant<']
    for pattern in invalid_patterns:
        if pattern in name.lower():
            return False
    
    # Verificar que está en la lista de tools válidas
    return name.lower() in VALID_TOOL_NAMES


# Comandos que indican que el usuario quiere continuar
CONTINUE_COMMANDS = {
    "continúa", "continua", "continue", "sigue", "adelante",
    "sí", "si", "yes", "ok", "vale", "prosigue", "go on",
    "sigue adelante", "continúa por favor", "sí continúa"
}

def _is_continue_command(query: str) -> bool:
    """
    Detecta si la query es un comando para continuar una tarea pausada.
    """
    query_lower = query.lower().strip()
    
    # Verificar comandos exactos o muy cortos
    if query_lower in CONTINUE_COMMANDS:
        return True
    
    # Verificar si contiene palabras clave de continuación
    continue_keywords = ["continúa", "continua", "sigue", "continue"]
    for keyword in continue_keywords:
        if keyword in query_lower and len(query_lower) < 50:
            return True
    
    return False


# ============================================
# System Prompts por Proveedor (en Español)
# ============================================

# Prompt base común en español
PROMPT_TOOLS_SECTION = """
## Herramientas de Sistema de Archivos
- `read_file`: Leer contenido de archivos
- `write_file`: Crear/sobrescribir archivos (SIEMPRE úsalo cuando pidan guardar algo)
- `edit_file`: Editar archivos (reemplazar texto)
- `list_directory`: Listar contenido de directorio
- `search_files`: Buscar archivos o contenido

## Herramientas de Ejecución
- `shell`: Ejecutar comandos de terminal
- `python`: Ejecutar código Python en Docker
- `javascript`: Ejecutar JavaScript en Docker

## Herramientas Web
- `web_search`: Buscar en internet
- `web_fetch`: Obtener contenido de URL

## Herramientas de Razonamiento
- `think`: Planificar y razonar sobre la tarea
- `reflect`: Evaluar resultados y progreso
- `plan`: Crear plan estructurado para tareas complejas
- `finish`: Dar respuesta final - DEBES llamar esto para completar

## Utilidades
- `calculate`: Evaluar expresiones matemáticas

## Delegación
- `delegate`: Delegar a subagentes especializados
"""

PROMPT_SUBAGENTS_SECTION = """
## Subagentes Especializados

Usa `delegate(agent="...", task="...")` para tareas específicas:

- **media_agent**: Generación de imágenes con DALL-E 3, Stable Diffusion, Flux
  Ejemplos: "Genera una imagen de...", "Crea un logo para...", "Dibuja..."

- **slides_agent**: Generación de presentaciones HTML profesionales
  Ejemplos: "Crea una presentación sobre...", "Genera slides de...", "Haz un PowerPoint de..."
  
  IMPORTANTE: Para presentaciones, usa la tool `generate_slides` directamente (NO delegate).
  Esta tool tiene streaming progresivo y mejor experiencia de usuario.
  
  FLUJO PARA PRESENTACIONES:
  1. Investiga el tema (usa web_search si necesitas datos actuales)
  2. Crea un outline JSON: title y slides array
  3. Llama: generate_slides(outline=json_del_outline, context=info_recopilada)
  
  Tipos de slide: title, content, bullets, stats, comparison, quote
  Cada slide tiene: title, type, content o bullets[], badge (opcional)
  
- **sap_agent** (próximamente): Consultas SAP S/4HANA y BIW
- **mail_agent** (próximamente): Gestión de correo
- **office_agent** (próximamente): Creación de documentos Office
"""

# ============================================
# Prompt para OLLAMA / Modelos Locales (Llama, Mistral, etc.)
# Más directo y explícito, sin mucha complejidad
# ============================================

PROMPT_OLLAMA = """Eres Brain 2.0, un asistente inteligente con acceso a herramientas.

IDIOMA: Responde SIEMPRE en español.

## REGLAS CRÍTICAS - LEE PRIMERO

1. DEBES llamar `finish` para completar CUALQUIER tarea
2. NO llames la misma herramienta más de 3 veces seguidas
3. Cuando termines, llama `finish` inmediatamente

## HERRAMIENTAS DISPONIBLES
{tools_section}
{subagents_section}

## FLUJO DE TRABAJO

{workflow_instructions}

## CUÁNDO LLAMAR `finish`

Llama `finish` AHORA si:
- Has escrito un archivo exitosamente
- Has ejecutado código y tienes resultados
- Has obtenido la información solicitada
- Has completado todas las partes de la tarea

## EJEMPLOS

- "Busca X y guárdalo" → web_search → write_file → finish
- "Lee archivo X" → read_file → finish
- "Genera una imagen" → delegate(agent="media_agent", task="...") → finish
- "Crea presentación sobre X" → web_search (si necesario) → generate_slides(outline=json) → finish

Ahora ayuda al usuario con su petición."""

# ============================================
# Prompt para OPENAI (GPT-4, GPT-4o, etc.)
# Estructurado con markdown, maneja complejidad bien
# ============================================

PROMPT_OPENAI = """Eres Brain 2.0, un asistente inteligente con acceso a herramientas.

# IDIOMA
**Responde SIEMPRE en español**, independientemente del idioma de la consulta.

# REGLAS CRÍTICAS

⚠️ **DEBES llamar la herramienta `finish` para completar cualquier tarea.**
⚠️ **NO llames la misma herramienta más de 3 veces consecutivas.**
⚠️ **Si has completado la tarea, llama `finish` inmediatamente.**

# PRINCIPIOS

1. **EFICIENCIA**: Usa el mínimo de llamadas necesarias
2. **USA HERRAMIENTAS**: Tienes herramientas potentes, úsalas
3. **EVITA LOOPS**: No repitas la misma herramienta sin progreso
4. **FINALIZA RÁPIDO**: Cuando termines, llama `finish` con tu respuesta
5. **DELEGA TAREAS ESPECIALIZADAS**: Para imágenes o tareas de dominio, usa `delegate`

# HERRAMIENTAS DISPONIBLES
{tools_section}
{subagents_section}

## Cuándo Delegar

✅ **DELEGA cuando**:
- El usuario pide generar/crear una imagen
- La tarea requiere conocimiento especializado (SAP, email, etc.)

❌ **NO DELEGUES cuando**:
- Puedes completar la tarea con tus herramientas core
- Es una tarea simple de archivos, web o código

# FLUJO DE TRABAJO

{workflow_instructions}

# REGLAS DE FINALIZACIÓN

1. **`finish` ES OBLIGATORIO**: Toda tarea DEBE terminar con `finish(final_answer="tu respuesta")`
2. **SIN LOOPS**: NO llames la misma herramienta más de 3 veces
3. **DESPUÉS de `write_file`** → La tarea suele estar completa. Llama `finish`
4. **DESPUÉS de `python`** → Reporta el resultado y llama `finish`
5. **DESPUÉS de `delegate`** → Incluye la respuesta del subagente e imágenes en tu respuesta
6. **FORMATO**: Usa markdown en tu respuesta final

# SEÑALES PARA LLAMAR `finish`

- Has escrito un archivo exitosamente
- Has ejecutado código y tienes resultados
- Has obtenido la información solicitada
- Un subagente ha completado su tarea
- Has llamado cualquier herramienta 3+ veces

# EJEMPLOS

- "Busca X y guarda en Y" → web_search → write_file → finish
- "Lee archivo X y analiza" → read_file → think → finish
- "Genera una imagen de un gato" → delegate(agent="media_agent", task="...") → finish

Ahora, ayuda al usuario con su petición."""

# ============================================
# Prompt para ANTHROPIC (Claude)
# Más conversacional, aprovecha el lenguaje natural
# ============================================

PROMPT_ANTHROPIC = """Eres Brain 2.0, un asistente inteligente con acceso a herramientas para ayudar a los usuarios.

Por favor, responde siempre en español.

## Tu Objetivo

Ayudar al usuario completando tareas de forma eficiente usando las herramientas disponibles. Cuando termines una tarea, siempre llama la herramienta `finish` con tu respuesta final.

## Herramientas Disponibles
{tools_section}
{subagents_section}

## Cómo Trabajar

{workflow_instructions}

## Puntos Importantes

- **Finalización**: Siempre termina llamando `finish(final_answer="tu respuesta")`. Es obligatorio.
- **Evita repeticiones**: Si has llamado la misma herramienta 3 veces sin progreso, para y llama `finish` con lo que tengas.
- **Delegación**: Para generar imágenes, usa `delegate(agent="media_agent", task="descripción")`.
- **Formato**: Usa markdown en tus respuestas para mejor legibilidad.

## Señales de que Debes Finalizar

Llama `finish` cuando:
- Hayas escrito un archivo exitosamente
- Hayas ejecutado código y tengas los resultados
- Hayas obtenido la información que pedía el usuario
- Un subagente haya completado su tarea
- Hayas intentado algo 3 veces sin éxito

## Ejemplos de Flujos

1. "Busca información sobre X" → web_search → finish (con la información)
2. "Crea un archivo con Y" → write_file → finish (confirmando la creación)
3. "Genera una imagen de Z" → delegate → finish (incluyendo la imagen generada)

Ahora, ¿en qué puedo ayudarte?"""

# ============================================
# Prompt para GOOGLE (Gemini)
# Similar a OpenAI pero con ajustes
# ============================================

PROMPT_GOOGLE = """Eres Brain 2.0, un asistente inteligente con acceso a herramientas.

**IDIOMA**: Responde siempre en español.

## Reglas Importantes

1. **Usa herramientas**: Tienes acceso a herramientas potentes. Úsalas para completar tareas.
2. **Finaliza con `finish`**: SIEMPRE termina llamando `finish(final_answer="tu respuesta")`.
3. **Evita loops**: No llames la misma herramienta más de 3 veces seguidas.
4. **Delega cuando sea necesario**: Para imágenes, usa el subagente media_agent.

## Herramientas Disponibles
{tools_section}
{subagents_section}

## Flujo de Trabajo

{workflow_instructions}

## Cuándo Finalizar

Llama `finish` inmediatamente cuando:
- Hayas escrito un archivo
- Hayas ejecutado código con resultados
- Hayas obtenido información solicitada
- Un subagente haya completado su trabajo

## Ejemplos

- Buscar y guardar: web_search → write_file → finish
- Generar imagen: delegate(agent="media_agent", task="...") → finish
- Analizar archivo: read_file → think → finish

Ayuda al usuario con su petición."""

# ============================================
# Workflows en Español
# ============================================

WORKFLOW_SIMPLE = """Para esta tarea SIMPLE:
1. Identifica qué herramienta(s) necesitas
2. Ejecuta la(s) herramienta(s) en orden
3. IMPORTANTE: Si la tarea tiene varias partes, completa TODAS
4. Llama `finish` con tu respuesta completa

Ejemplo: "Calcula X" → calculate → finish"""

WORKFLOW_MODERATE = """Para esta tarea MODERADA:
1. Usa `think` para dividir la tarea en pasos
2. Ejecuta cada paso con las herramientas apropiadas
3. IMPORTANTE: Completa TODAS las partes antes de finalizar
4. Si piden guardar algo, DEBES usar `write_file`
5. Usa `reflect` si los resultados parecen incompletos
6. Llama `finish` con tu respuesta completa

Ejemplo: "Busca X y guárdalo en Y" → think → web_search → write_file → finish"""

WORKFLOW_COMPLEX = """Para esta tarea COMPLEJA:
1. Usa `plan` para crear un enfoque estructurado con TODOS los pasos
2. Usa `think` antes de cada paso importante
3. Ejecuta herramientas según tu plan - NO saltes ningún paso
4. Usa `reflect` para verificar progreso después de cada acción
5. CHECKPOINT: Antes de finalizar, verifica que TODAS las partes estén hechas
6. Si falta algo, ejecuta las herramientas necesarias
7. Llama `finish` con tu respuesta completa

Ejemplo: "Investiga X, analiza Y, crea informe Z" → plan → web_search → think → write → reflect → finish"""

# ============================================
# Función para obtener prompt según proveedor
# ============================================

def get_system_prompt_for_provider(provider_type: str) -> str:
    """
    Devuelve el system prompt optimizado para el proveedor LLM.
    
    Args:
        provider_type: Tipo de proveedor (ollama, openai, anthropic, google, openrouter)
    
    Returns:
        Template del system prompt (necesita .format() con workflow_instructions)
    """
    prompts = {
        "ollama": PROMPT_OLLAMA,
        "openai": PROMPT_OPENAI,
        "anthropic": PROMPT_ANTHROPIC,
        "google": PROMPT_GOOGLE,
        "openrouter": PROMPT_OPENAI,  # OpenRouter usa formato similar a OpenAI
    }
    
    base_prompt = prompts.get(provider_type, PROMPT_OPENAI)
    
    # Insertar secciones comunes
    return base_prompt.format(
        tools_section=PROMPT_TOOLS_SECTION,
        subagents_section=PROMPT_SUBAGENTS_SECTION,
        workflow_instructions="{workflow_instructions}"  # Mantener placeholder
    )

# Mantener compatibilidad con código existente
ADAPTIVE_AGENT_SYSTEM_PROMPT = get_system_prompt_for_provider("openai")


# ============================================
# Chain Definition
# ============================================

ADAPTIVE_AGENT_DEFINITION = ChainDefinition(
    id="adaptive",
    name="Brain 2.0 Adaptive Agent",
    description="Agente inteligente con razonamiento adaptativo y 15 core tools",
    type="agent",
    version="2.0.0",
    nodes=[
        NodeDefinition(
            id="adaptive_agent",
            type=NodeType.LLM,
            name="Adaptive Agent",
            system_prompt=ADAPTIVE_AGENT_SYSTEM_PROMPT,
            temperature=0.5
        )
    ],
    config=ChainConfig(
        temperature=0.5,
        use_memory=True,
        max_memory_messages=10
    )
)


# ============================================
# Builder Function
# ============================================

async def build_adaptive_agent(
    config: ChainConfig,
    llm_url: str,
    model: str,
    input_data: dict,
    memory: list,
    execution_id: str = "",
    stream: bool = True,
    provider_type: str = "ollama",
    api_key: Optional[str] = None,
    emit_brain_events: bool = False,
    **kwargs
) -> AsyncGenerator[StreamEvent, None]:
    """
    Builder del Adaptive Agent de Brain 2.0.
    
    Flujo:
    1. Detectar complejidad de la query
    2. Configurar modo de razonamiento
    3. Loop de tool calling hasta finish
    
    Args:
        emit_brain_events: Si True, emite Brain Events (markers HTML) para Open WebUI
    """
    # Importar helpers de Brain Events
    from ..brain_events import (
        create_thinking_event,
        create_action_event,
        create_sources_event,
        get_action_type_for_tool,
        get_action_title_for_tool
    )
    
    query = input_data.get("message", input_data.get("query", ""))
    
    # Detectar si es una orden de continuar desde límite anterior
    is_continue_request = _is_continue_command(query)
    
    logger.info(
        "🧠 Brain 2.0 Adaptive Agent starting",
        query=query[:100],
        model=model,
        provider=provider_type,
        is_continue=is_continue_request
    )
    
    # ========== FASE 1: ANÁLISIS DE COMPLEJIDAD ==========
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="complexity_analysis",
        node_name="Analyzing task complexity",
        data={"query": query[:100]}
    )
    
    # Detectar complejidad
    complexity_analysis = detect_complexity(query)
    reasoning_config = get_reasoning_config(complexity_analysis.level)
    
    yield StreamEvent(
        event_type="node_end",
        execution_id=execution_id,
        node_id="complexity_analysis",
        data={
            "complexity": complexity_analysis.level.value,
            "reasoning_mode": reasoning_config.mode.value,
            "estimated_tools": complexity_analysis.estimated_tools
        }
    )
    
    # Emitir Brain Event de thinking inicial
    if emit_brain_events:
        yield StreamEvent(
            event_type="token",
            execution_id=execution_id,
            node_id="brain_thinking",
            content=create_thinking_event(
                f"Analizando solicitud...\n\nComplejidad: {complexity_analysis.level.value}\nHerramientas estimadas: {complexity_analysis.estimated_tools}",
                status="start"
            )
        )
    
    # Seleccionar workflow según complejidad
    if complexity_analysis.level == ComplexityLevel.COMPLEX:
        workflow = WORKFLOW_COMPLEX
    elif complexity_analysis.level == ComplexityLevel.MODERATE:
        workflow = WORKFLOW_MODERATE
    else:
        workflow = WORKFLOW_SIMPLE
    
    # ========== FASE 2: PREPARAR TOOLS Y MENSAJES ==========
    
    # Registrar core tools si no están registradas
    tool_registry.register_core_tools()
    
    # Obtener tools en formato LLM
    tools = tool_registry.get_tools_for_llm()
    
    logger.info(f"📦 {len(tools)} core tools loaded")
    
    # Obtener prompt optimizado para el proveedor
    provider_prompt = get_system_prompt_for_provider(provider_type)
    
    # Construir system prompt con workflow
    system_prompt = provider_prompt.format(
        workflow_instructions=workflow
    )
    
    logger.info(f"📝 Using prompt optimized for provider: {provider_type}")
    
    # Construir mensajes con memoria
    messages = [{"role": "system", "content": system_prompt}]
    
    # Agregar memoria (últimos N mensajes)
    if memory and config.use_memory:
        max_memory = config.max_memory_messages or 10
        for msg in memory[-max_memory:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
    
    # Agregar query actual
    messages.append({"role": "user", "content": query})
    
    # ========== FASE 3: LOOP DE TOOL CALLING ==========
    
    # Usar max_iterations de la config (configurable por usuario) o el default del reasoning
    base_max_iterations = config.max_iterations if hasattr(config, 'max_iterations') and config.max_iterations else reasoning_config.max_iterations
    ask_before_continue = config.ask_before_continue if hasattr(config, 'ask_before_continue') else True
    
    # Si es un comando de continuar, aumentar el límite
    if is_continue_request:
        max_iterations = base_max_iterations * 2  # Dar el doble de iteraciones
        logger.info(f"🔄 Continue request detected, increasing max_iterations to {max_iterations}")
        
        # Emitir evento informando que continúa
        yield StreamEvent(
            event_type="node_start",
            execution_id=execution_id,
            node_id="continue_execution",
            node_name="Continuando ejecución",
            data={"extended_iterations": max_iterations}
        )
    else:
        max_iterations = base_max_iterations
    
    tool_results = []
    iteration = 0
    final_answer = None
    iteration_limit_reached = False
    
    # Detección de loops
    consecutive_same_tool = 0
    last_tool_name = None
    MAX_CONSECUTIVE_SAME_TOOL = 3
    
    while iteration < max_iterations:
        iteration += 1
        
        yield StreamEvent(
            event_type="node_start",
            execution_id=execution_id,
            node_id=f"iteration_{iteration}",
            node_name=f"Iteration {iteration}/{max_iterations}",
            data={"iteration": iteration}
        )
        
        try:
            # Llamar al LLM con tools
            response: LLMToolResponse = await call_llm_with_tools(
                llm_url=llm_url,
                model=model,
                messages=messages,
                tools=tools,
                temperature=reasoning_config.temperature,
                provider_type=provider_type,
                api_key=api_key
            )
            
            # ========== CASO 1: SOLO CONTENIDO (sin tools) ==========
            if response.content and not response.tool_calls:
                logger.info(f"📝 LLM provided direct response (iteration {iteration})")
                
                # Si el modelo responde sin usar finish, tratarlo como respuesta final
                final_answer = response.content
                
                yield StreamEvent(
                    event_type="token",
                    execution_id=execution_id,
                    node_id="",
                    content=response.content
                )
                
                yield StreamEvent(
                    event_type="node_end",
                    execution_id=execution_id,
                    node_id=f"iteration_{iteration}",
                    data={"direct_response": True}
                )
                break
            
            # ========== CASO 2: TOOL CALLS ==========
            if response.tool_calls:
                # Agregar mensaje del assistant con tool_calls
                if provider_type != "ollama":
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.get("name"),
                                "arguments": tc.function.get("arguments", "{}")
                            }
                        } for tc in response.tool_calls]
                    })
                
                # Ejecutar cada tool
                for tool_call in response.tool_calls:
                    tool_name = tool_call.function.get("name", "")
                    
                    # Validar nombre de tool (filtrar artifacts de modelos)
                    if not is_valid_tool_name(tool_name):
                        logger.warning(
                            f"⚠️ Ignorando tool inválida: {tool_name}",
                            tool_name=tool_name
                        )
                        continue
                    
                    tool_args_str = tool_call.function.get("arguments", "{}")
                    
                    # Parsear argumentos
                    try:
                        tool_args = json.loads(tool_args_str) if isinstance(tool_args_str, str) else tool_args_str
                    except json.JSONDecodeError:
                        tool_args = {}
                    
                    logger.info(f"🔧 Executing tool: {tool_name}", args=list(tool_args.keys()))
                    
                    # Detección de loops - track consecutive same tool calls
                    if tool_name == last_tool_name:
                        consecutive_same_tool += 1
                    else:
                        consecutive_same_tool = 1
                        last_tool_name = tool_name
                    
                    # Si se detecta loop, añadir advertencia para la siguiente iteración
                    if consecutive_same_tool >= MAX_CONSECUTIVE_SAME_TOOL and tool_name != "finish":
                        logger.warning(f"⚠️ Loop detected: {tool_name} called {consecutive_same_tool} times")
                    
                    # Determinar nombre amigable para la GUI
                    tool_display_names = {
                        "think": "💭 Pensando",
                        "reflect": "🔍 Reflexionando", 
                        "plan": "📋 Planificando",
                        "read_file": "📖 Leyendo archivo",
                        "write_file": "✍️ Escribiendo archivo",
                        "edit_file": "✏️ Editando archivo",
                        "list_directory": "📁 Listando directorio",
                        "search_files": "🔎 Buscando en archivos",
                        "shell": "💻 Ejecutando comando",
                        "python": "🐍 Ejecutando Python",
                        "javascript": "📜 Ejecutando JavaScript",
                        "web_search": "🌐 Buscando en web",
                        "web_fetch": "📥 Obteniendo URL",
                        "calculate": "🔢 Calculando",
                        "delegate": "🤖 Delegando a subagente",
                        "finish": "✅ Finalizando"
                    }
                    display_name = tool_display_names.get(tool_name, f"🔧 {tool_name}")
                    
                    # Yield evento de tool call (node_start para la GUI)
                    yield StreamEvent(
                        event_type="node_start",
                        execution_id=execution_id,
                        node_id=f"tool_{tool_name}_{iteration}",
                        node_name=display_name,
                        data={"tool": tool_name, "arguments": tool_args}
                    )
                    
                    # Emitir Brain Event de action start
                    if emit_brain_events:
                        action_type = get_action_type_for_tool(
                            tool_name,
                            agent=tool_args.get("agent") if tool_name == "delegate" else None
                        )
                        action_title = get_action_title_for_tool(tool_name, tool_args)
                        
                        yield StreamEvent(
                            event_type="token",
                            execution_id=execution_id,
                            node_id="brain_action",
                            content=create_action_event(
                                action_type=action_type,
                                title=action_title,
                                status="running"
                            )
                        )
                    
                    # Preparar argumentos para ejecución
                    exec_args = tool_args.copy()
                    
                    # Para delegate, inyectar contexto LLM interno
                    if tool_name == "delegate":
                        exec_args["_llm_url"] = llm_url
                        exec_args["_model"] = model
                        exec_args["_provider_type"] = provider_type
                        exec_args["_api_key"] = api_key
                    
                    # Para generate_slides, inyectar contexto LLM
                    if tool_name == "generate_slides":
                        exec_args["_llm_url"] = llm_url
                        exec_args["_model"] = model
                        exec_args["_provider_type"] = provider_type
                        exec_args["_api_key"] = api_key
                    
                    # Ejecutar tool
                    result = await tool_registry.execute(tool_name, **exec_args)
                    
                    # Emitir eventos capturados de generate_slides
                    if tool_name == "generate_slides" and emit_brain_events:
                        # Los eventos están en result.events_emitted
                        events_emitted = result.get("events_emitted", [])
                        for event_marker in events_emitted:
                            yield StreamEvent(
                                event_type="token",
                                execution_id=execution_id,
                                node_id="slides_streaming",
                                content=event_marker
                            )
                        
                        # Si tuvo éxito, terminar con el resultado
                        if result.get("success"):
                            final_msg = f"\n✅ {result.get('message', 'Presentación generada')}\n"
                            yield StreamEvent(
                                event_type="token",
                                execution_id=execution_id,
                                node_id="",
                                content=final_msg
                            )
                            break
                    
                    # Verificar si es finish
                    if tool_name == "finish":
                        final_answer = result.get("final_answer", "")
                        
                        yield StreamEvent(
                            event_type="node_end",
                            execution_id=execution_id,
                            node_id=f"tool_{tool_name}_{iteration}",
                            data={"tool": tool_name, "done": True, "thinking": final_answer}
                        )
                        
                        # Emitir respuesta final
                        yield StreamEvent(
                            event_type="token",
                            execution_id=execution_id,
                            node_id="",
                            content=final_answer
                        )
                        break
                    
                    # Guardar resultado
                    tool_results.append({
                        "tool": tool_name,
                        "result": result
                    })
                    
                    # Emitir Brain Events post-tool
                    if emit_brain_events:
                        # Action complete
                        action_type = get_action_type_for_tool(
                            tool_name,
                            agent=tool_args.get("agent") if tool_name == "delegate" else None
                        )
                        action_title = get_action_title_for_tool(tool_name, tool_args)
                        
                        # Contar resultados si aplica
                        results_count = None
                        if tool_name == "web_search" and isinstance(result, dict):
                            # web_search puede devolver lista de resultados
                            if "results" in result:
                                results_count = len(result.get("results", []))
                            elif "sources" in result:
                                results_count = len(result.get("sources", []))
                        
                        yield StreamEvent(
                            event_type="token",
                            execution_id=execution_id,
                            node_id="brain_action",
                            content=create_action_event(
                                action_type=action_type,
                                title=action_title,
                                status="completed",
                                results_count=results_count
                            )
                        )
                        
                        # Emitir sources para web_search
                        if tool_name == "web_search" and isinstance(result, dict):
                            sources = result.get("results") or result.get("sources") or []
                            if sources:
                                yield StreamEvent(
                                    event_type="token",
                                    execution_id=execution_id,
                                    node_id="brain_sources",
                                    content=create_sources_event(sources)
                                )
                        
                        # Emitir thinking para tools de razonamiento
                        if tool_name in ("think", "reflect", "plan"):
                            thinking = result.get("thinking") or result.get("reflection") or result.get("plan") or ""
                            if thinking:
                                yield StreamEvent(
                                    event_type="token",
                                    execution_id=execution_id,
                                    node_id="brain_thinking",
                                    content=create_thinking_event(thinking, status="progress")
                                )
                    
                    # Manejar delegación especial
                    if tool_name == "delegate" and result.get("success"):
                        # Imágenes de media_agent
                        if result.get("images"):
                            for img in result["images"]:
                                if img.get("url"):
                                    yield StreamEvent(
                                        event_type="image",
                                        execution_id=execution_id,
                                        node_id=f"tool_{tool_name}_{iteration}",
                                        data={
                                            "image_url": img["url"],
                                            "alt_text": img.get("prompt", "Generated image"),
                                            "provider": img.get("provider"),
                                            "model": img.get("model")
                                        }
                                    )
                                elif img.get("base64"):
                                    yield StreamEvent(
                                        event_type="image",
                                        execution_id=execution_id,
                                        node_id=f"tool_{tool_name}_{iteration}",
                                        data={
                                            "image_data": img["base64"],
                                            "mime_type": img.get("mime_type", "image/png"),
                                            "alt_text": img.get("prompt", "Generated image")
                                        }
                                    )
                        
                        # Respuestas de slides_agent con Brain Events
                        # Emitir directamente al stream para que Open WebUI los procese
                        response_text = result.get("response", "")
                        if "<!--BRAIN_EVENT:" in response_text:
                            yield StreamEvent(
                                event_type="token",
                                execution_id=execution_id,
                                node_id=f"subagent_{result.get('agent_id', 'unknown')}",
                                content=response_text
                            )
                            # La presentación ya se generó, terminar
                            final_answer = f"Presentación generada: {result.get('data', {}).get('title', 'Sin título')} ({result.get('data', {}).get('slides_count', '?')} slides)"
                            yield StreamEvent(
                                event_type="token",
                                execution_id=execution_id,
                                node_id="",
                                content=final_answer
                            )
                            break
                    
                    # Extraer contenido para herramientas de razonamiento
                    thinking_content = None
                    if tool_name in ("think", "reflect", "plan"):
                        # Estas herramientas devuelven contenido de pensamiento
                        thinking_content = result.get("thinking") or result.get("reflection") or result.get("plan") or result.get("result", "")
                    
                    # Crear preview del resultado
                    if thinking_content:
                        preview = thinking_content[:500] + "..." if len(thinking_content) > 500 else thinking_content
                    else:
                        preview = str(result)[:200]
                    
                    yield StreamEvent(
                        event_type="node_end",
                        execution_id=execution_id,
                        node_id=f"tool_{tool_name}_{iteration}",
                        data={
                            "tool": tool_name,
                            "success": result.get("success", True),
                            "thinking": thinking_content,  # Para herramientas de razonamiento
                            "observation": preview if not thinking_content else None,  # Para otras herramientas
                            "result_preview": preview
                        }
                    )
                    
                    # Agregar resultado a mensajes
                    result_str = json.dumps(result, ensure_ascii=False, default=str)
                    if len(result_str) > 4000:
                        result_str = result_str[:4000] + "... [truncated]"
                    
                    if provider_type == "ollama":
                        messages.append({
                            "role": "tool",
                            "content": result_str
                        })
                    else:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": tool_name,
                            "content": result_str
                        })
                
                # Si encontramos finish, salir del loop
                if final_answer is not None:
                    yield StreamEvent(
                        event_type="node_end",
                        execution_id=execution_id,
                        node_id=f"iteration_{iteration}",
                        data={"finished": True}
                    )
                    break
                
                # Si se detectó un loop, inyectar advertencia al LLM
                if consecutive_same_tool >= MAX_CONSECUTIVE_SAME_TOOL:
                    loop_warning = f"""⚠️ WARNING: You have called `{last_tool_name}` {consecutive_same_tool} times consecutively.

STOP and call `finish` NOW with your current results. Do NOT call {last_tool_name} again.

If the task is complete, use: finish(final_answer="your answer here")
If you need something else, use a DIFFERENT tool."""
                    
                    messages.append({"role": "system", "content": loop_warning})
                    logger.info(f"⚠️ Injected loop warning after {consecutive_same_tool}x {last_tool_name}")
            
            yield StreamEvent(
                event_type="node_end",
                execution_id=execution_id,
                node_id=f"iteration_{iteration}",
                data={"tools_used": len(response.tool_calls) if response.tool_calls else 0}
            )
            
        except Exception as e:
            logger.error(f"Error in iteration {iteration}: {e}", exc_info=True)
            
            yield StreamEvent(
                event_type="error",
                execution_id=execution_id,
                node_id=f"iteration_{iteration}",
                content=f"Error: {str(e)}"
            )
            
            # Continuar al siguiente intento
            continue
    
    # ========== FASE 4: FINALIZACIÓN ==========
    
    # Verificar si llegamos al límite sin finalizar
    if final_answer is None and iteration >= max_iterations:
        iteration_limit_reached = True
        logger.info(f"⚠️ Iteration limit reached ({max_iterations})")
        
        # Construir resumen de lo que se hizo
        tools_summary = ", ".join([tr["tool"] for tr in tool_results]) if tool_results else "ninguna"
        
        if ask_before_continue:
            # Emitir evento especial para que el frontend pregunte al usuario
            continue_message = f"""He llegado al límite de {max_iterations} iteraciones configurado.

**Progreso actual:**
- Iteraciones usadas: {iteration}
- Herramientas utilizadas: {tools_summary}
- Tareas completadas: {len(tool_results)} acciones

¿Quieres que continúe trabajando en la tarea? Responde **"continúa"** para seguir o **"finaliza"** para obtener un resumen de lo realizado."""
            
            yield StreamEvent(
                event_type="iteration_limit",
                execution_id=execution_id,
                node_id="limit_reached",
                node_name="Límite de iteraciones alcanzado",
                content=continue_message,
                data={
                    "iterations_used": iteration,
                    "max_iterations": max_iterations,
                    "tools_used": [tr["tool"] for tr in tool_results],
                    "can_continue": True
                }
            )
            
            # Emitir también como token para que el usuario vea el mensaje
            yield StreamEvent(
                event_type="token",
                execution_id=execution_id,
                node_id="",
                content=continue_message
            )
            
            # Finalizar esta ejecución - el usuario puede continuar con un nuevo mensaje
            yield StreamEvent(
                event_type="response_complete",
                execution_id=execution_id,
                node_id="adaptive_agent",
                content=continue_message,
                data={
                    "complexity": complexity_analysis.level.value,
                    "iterations": iteration,
                    "tools_used": [tr["tool"] for tr in tool_results],
                    "iteration_limit_reached": True,
                    "can_continue": True
                }
            )
            
            yield {
                "_result": {
                    "response": continue_message,
                    "complexity": complexity_analysis.level.value,
                    "reasoning_mode": reasoning_config.mode.value,
                    "iterations": iteration,
                    "tools_used": [tr["tool"] for tr in tool_results],
                    "iteration_limit_reached": True
                }
            }
            return
    
    if final_answer is None:
        # Intentar forzar una respuesta final del LLM
        logger.info("⚠️ No finish called, forcing final response")
        
        # Construir resumen de lo que se hizo
        tools_summary = ", ".join([tr["tool"] for tr in tool_results]) if tool_results else "ninguna"
        
        # Pedir al LLM que genere una respuesta final
        force_finish_prompt = f"""You have completed {iteration} iterations using these tools: {tools_summary}.

Now you MUST provide your final answer using the `finish` tool. Summarize what was accomplished and provide the answer to the user's original request.

IMPORTANT: You MUST call the `finish` tool now with your complete answer."""
        
        messages.append({"role": "user", "content": force_finish_prompt})
        
        try:
            # Una última llamada para obtener finish
            final_response = await call_llm_with_tools(
                llm_url=llm_url,
                model=model,
                messages=messages,
                tools=tools,
                temperature=0.3,  # Más determinístico para finish
                provider_type=provider_type,
                api_key=api_key
            )
            
            # Procesar respuesta
            if final_response.tool_calls:
                for tc in final_response.tool_calls:
                    if tc.function.get("name") == "finish":
                        try:
                            args = json.loads(tc.function.get("arguments", "{}"))
                            final_answer = args.get("answer", args.get("final_answer", ""))
                        except:
                            final_answer = tc.function.get("arguments", "")
                        break
            
            if not final_answer and final_response.content:
                final_answer = final_response.content
                
        except Exception as e:
            logger.error(f"Error forcing finish: {e}")
        
        # Si aún no hay respuesta, usar los resultados de las herramientas
        if not final_answer:
            if tool_results:
                # Intentar extraer información útil de los resultados
                last_results = tool_results[-3:]  # Últimos 3 resultados
                summary_parts = []
                for tr in last_results:
                    result = tr.get("result", {})
                    if isinstance(result, dict):
                        if "content" in result:
                            summary_parts.append(str(result["content"])[:500])
                        elif "data" in result:
                            summary_parts.append(str(result["data"])[:500])
                
                if summary_parts:
                    final_answer = "Resultados obtenidos:\n\n" + "\n\n".join(summary_parts)
                else:
                    final_answer = f"Tarea procesada usando: {tools_summary}. Consulta los archivos generados para ver los resultados."
            else:
                final_answer = "No se pudo completar la tarea. Por favor, reformula tu petición."
        
        yield StreamEvent(
            event_type="token",
            execution_id=execution_id,
            node_id="",
            content=final_answer
        )
    
    # Evento de completado
    yield StreamEvent(
        event_type="response_complete",
        execution_id=execution_id,
        node_id="adaptive_agent",
        content=final_answer,
        data={
            "complexity": complexity_analysis.level.value,
            "iterations": iteration,
            "tools_used": [tr["tool"] for tr in tool_results]
        }
    )
    
    # Resultado para el executor
    yield {
        "_result": {
            "response": final_answer,
            "complexity": complexity_analysis.level.value,
            "reasoning_mode": reasoning_config.mode.value,
            "iterations": iteration,
            "tools_used": [tr["tool"] for tr in tool_results]
        }
    }


# ============================================
# Registro del Agente
# ============================================

def register_adaptive_agent():
    """Registrar el Adaptive Agent en el registry"""
    
    chain_registry.register(
        chain_id="adaptive",
        definition=ADAPTIVE_AGENT_DEFINITION,
        builder=build_adaptive_agent
    )
    
    logger.info("✅ Brain 2.0 Adaptive Agent registered (v2.0.0)")
