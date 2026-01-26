"""
Admin Orchestrator Agent - Coordinador de tareas administrativas

Este agente es un orquestador de ALTO NIVEL que coordina tareas administrativas complejas.
NO ejecuta código directamente, sino que delega a agentes especializados:

ARQUITECTURA:
┌─────────────────────────────────┐
│  Admin Orchestrator Agent       │ ← Coordinador (este agente)
│  - Analiza petición             │
│  - Decide estrategia            │
│  - Consulta RAG si necesario    │
│  - Delega a ejecutores          │
└─────────────────────────────────┘
          │
          ├─→ Persistent Admin Agent (ejecución de código)
          ├─→ RAG Agent (conocimiento sobre webs, APIs, etc.)
          ├─→ Tool Agent (herramientas básicas)
          └─→ Conversational (explicaciones)

CASOS DE USO:
1. Descargas complejas que requieren conocimiento previo del sitio
2. Tareas que combinan múltiples operaciones administrativas
3. Monitoreo y automatización con múltiples pasos
4. Integración de datos de múltiples fuentes

DELEGACIÓN:
- Si la tarea es directa (ej: "ejecuta este script") → Persistent Admin
- Si necesita info sobre cómo hacer algo → RAG + Persistent Admin
- Si necesita análisis previo → Tool Agent + Persistent Admin
"""

import json
from typing import AsyncGenerator, Optional, Dict, Any, List

from ..models import (
    ChainDefinition,
    ChainConfig,
    NodeDefinition,
    NodeType,
    StreamEvent
)
from ..registry import chain_registry
from .llm_utils import call_llm, call_llm_stream
from .agent_helpers import (
    extract_json,
    build_llm_messages
)

import structlog

logger = structlog.get_logger()


# ============================================
# Funciones del Admin Orchestrator
# ============================================

def get_admin_agents() -> Dict[str, Dict[str, str]]:
    """
    Obtener agentes disponibles para delegación administrativa.
    """
    admin_agents = {
        "persistent_admin": {
            "name": "Persistent Admin Agent",
            "description": "Ejecuta código Python en contenedor permanente. Tiene acceso a red, volumen persistente y bibliotecas para web scraping, scheduling, database, etc.",
            "use_when": "Necesitas ejecutar código Python, descargar archivos, programar tareas, acceder a bases de datos."
        },
        "rag": {
            "name": "RAG Agent",
            "description": "Busca información en documentos guardados, manuales, guías y conocimiento previo del sistema.",
            "use_when": "Necesitas información sobre cómo funciona un sitio web, API, o recordar conocimiento previo."
        },
        "tool_agent": {
            "name": "Tool Agent",
            "description": "Herramientas básicas: cálculos, fecha/hora, conversiones, búsquedas web simples.",
            "use_when": "Necesitas obtener información básica, calcular algo, o buscar en web."
        },
        "conversational": {
            "name": "Conversational Agent",
            "description": "Conversación general y explicaciones.",
            "use_when": "Necesitas explicar algo al usuario sin ejecutar código."
        }
    }
    
    return admin_agents


async def execute_admin_subagent(
    agent_id: str,
    task: str,
    context: str,
    llm_url: str,
    model: str,
    config: ChainConfig,
    execution_id: str,
    provider_type: str = "ollama",
    api_key: Optional[str] = None,
    memory: Optional[list] = None
) -> Dict[str, Any]:
    """
    Ejecutar un sub-agente administrativo y capturar su resultado.
    """
    builder = chain_registry.get_builder(agent_id)
    definition = chain_registry.get(agent_id)
    
    if not builder or not definition:
        return {
            "success": False,
            "error": f"Agente '{agent_id}' no encontrado",
            "response": None
        }
    
    try:
        message = task
        if context and context != "Sin contexto previo":
            message = f"{task}\n\nCONTEXTO:\n{context}"
        
        sub_input = {
            "message": message,
            "query": message
        }
        
        full_response = ""
        
        async for event in builder(
            config=definition.config,
            llm_url=llm_url,
            model=model,
            input_data=sub_input,
            memory=memory or [],
            execution_id=f"{execution_id}_admin_sub_{agent_id}",
            stream=False,
            provider_type=provider_type,
            api_key=api_key
        ):
            if isinstance(event, dict) and "_result" in event:
                result = event["_result"]
                full_response = result.get("response", "")
                break
            
            if hasattr(event, 'event_type'):
                if event.event_type == "token" and event.content:
                    full_response += event.content
                elif event.event_type == "node_end" and event.data:
                    if "response" in event.data:
                        full_response = event.data["response"]
        
        return {
            "success": True,
            "response": full_response,
            "agent_name": definition.name
        }
        
    except Exception as e:
        logger.error(f"Error ejecutando sub-agente admin {agent_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "response": None
        }


# ============================================
# Definición del Admin Orchestrator
# ============================================

ADMIN_ORCHESTRATOR_DEFINITION = ChainDefinition(
    id="admin_orchestrator",
    name="Admin Orchestrator Agent",
    description="Coordinador de tareas administrativas que delega a agentes especializados (Persistent Admin, RAG, etc.) para descargas web, automatización y monitoreo.",
    type="agent",
    version="1.0.0",
    nodes=[
        NodeDefinition(
            id="input",
            type=NodeType.INPUT,
            name="Petición Administrativa"
        ),
        NodeDefinition(
            id="analyzer",
            type=NodeType.LLM,
            name="Analizador de Estrategia",
            system_prompt="""Eres un coordinador experto en tareas administrativas y automatización.

Tu trabajo es analizar peticiones del usuario y decidir la ESTRATEGIA de ejecución.

AGENTES DISPONIBLES:
- persistent_admin: Ejecuta código Python (scraping, descargas, scheduling, DB access)
- rag: Busca información en documentos/conocimiento previo
- tool_agent: Herramientas básicas (cálculos, web search, fecha/hora)
- conversational: Explicaciones y conversación

PETICIÓN DEL USUARIO:
{{user_query}}

ANÁLISIS REQUERIDO:
1. ¿Qué tipo de tarea administrativa es?
   - download: Descargar archivos de la web
   - scraping: Extraer datos de páginas web
   - monitoring: Monitorear cambios en web/API
   - scheduling: Programar tareas periódicas
   - integration: Integrar con sistemas externos
   - execution: Ejecutar código/script existente
   - other: Otra tarea administrativa

2. ¿Necesita información previa?
   - ¿Conocemos el sitio web/API? → Consultar RAG
   - ¿Es un sitio nuevo? → Puede requerir exploración

3. ¿Qué estrategia seguir?
   - DIRECTA: Delegar directamente a persistent_admin
   - CON_CONOCIMIENTO: RAG → persistent_admin (para sitios conocidos)
   - EXPLORATORIA: tool_agent → persistent_admin (para sitios nuevos)
   - MULTI_PASO: Varios agentes en secuencia

PATRONES COMUNES:
- "Descarga X de sitio conocido" → RAG + persistent_admin
- "Descarga X de sitio nuevo" → Directa a persistent_admin (él explorará)
- "Programa tarea que haga X" → persistent_admin directo
- "Monitorea Y y avisa si cambia" → persistent_admin directo

RESPONDE EN JSON:
```json
{
  "task_type": "download|scraping|monitoring|scheduling|integration|execution|other",
  "complexity": "simple|medium|complex",
  "strategy": "DIRECTA|CON_CONOCIMIENTO|EXPLORATORIA|MULTI_PASO",
  "needs_knowledge": true/false,
  "knowledge_query": "qué buscar en RAG (si needs_knowledge=true)",
  "execution_plan": [
    {"step": 1, "agent": "agent_id", "task": "descripción específica"},
    {"step": 2, "agent": "agent_id", "task": "descripción específica"}
  ],
  "reasoning": "Breve explicación de la estrategia elegida"
}
```

IMPORTANTE:
- Sé pragmático: si es simple, usa estrategia DIRECTA
- El persistent_admin es muy capaz, confía en él para explorar sitios
- Solo usa RAG si realmente crees que tenemos info guardada sobre ese sitio/API
- Máximo 3 pasos en el plan""",
            prompt_template="Analiza la estrategia.",
            temperature=0.2
        ),
        NodeDefinition(
            id="knowledge_gatherer",
            type=NodeType.TOOL,
            name="Recopilador de Conocimiento",
            system_prompt="Delega a RAG para obtener información relevante."
        ),
        NodeDefinition(
            id="executor",
            type=NodeType.TOOL,
            name="Ejecutor de Plan"
        ),
        NodeDefinition(
            id="synthesizer",
            type=NodeType.LLM,
            name="Sintetizador",
            system_prompt="""Presenta los resultados de la coordinación administrativa al usuario.

PETICIÓN ORIGINAL:
{{user_query}}

ESTRATEGIA USADA:
{{strategy}}

PASOS EJECUTADOS:
{{steps_summary}}

RESULTADO FINAL:
{{final_result}}

Tu trabajo:
1. Explicar qué se hizo para completar la petición
2. Presentar resultados claramente
3. Si hubo errores o problemas, mencionarlos
4. Sugerir próximos pasos o mejoras
5. Si se guardaron scripts/archivos, indicar ubicación

TONO:
- Conciso pero completo
- Enfocado en el resultado
- Accionable (qué puede hacer el usuario ahora)

Genera la respuesta final.""",
            prompt_template="Presenta los resultados.",
            temperature=0.5
        ),
        NodeDefinition(
            id="output",
            type=NodeType.OUTPUT,
            name="Respuesta"
        )
    ],
    config=ChainConfig(
        temperature=0.4,
        use_memory=True,
        max_memory_messages=10
    )
)


# ============================================
# Builder Function
# ============================================

async def build_admin_orchestrator_agent(
    config: ChainConfig,
    llm_url: str,
    model: str,
    input_data: dict,
    memory: list,
    execution_id: str = "",
    stream: bool = True,
    provider_type: str = "ollama",
    api_key: Optional[str] = None,
    **kwargs
) -> AsyncGenerator[StreamEvent, None]:
    """
    Builder del coordinador administrativo.
    
    FASES:
    1. Analysis: Analizar tarea y decidir estrategia
    2. Knowledge Gathering: Consultar RAG si es necesario
    3. Execution: Ejecutar plan delegando a agentes
    4. Synthesis: Presentar resultados coordinados
    
    NODOS:
    - input: Petición administrativa del usuario
    - analyzer: Analiza y decide estrategia
    - knowledge_gatherer: Consulta RAG si necesario
    - executor: Ejecuta plan paso a paso
    - synthesizer: Presenta resultados finales
    - output: Respuesta completa
    
    MEMORY: Yes (últimos 10 mensajes)
    DELEGATION: persistent_admin, rag, tool_agent, conversational
    """
    
    query = input_data.get("message", input_data.get("query", ""))
    
    # Obtener nodos
    analyzer_node = ADMIN_ORCHESTRATOR_DEFINITION.get_node("analyzer")
    synth_node = ADMIN_ORCHESTRATOR_DEFINITION.get_node("synthesizer")
    
    if not all([analyzer_node, synth_node]):
        raise ValueError("Nodos del Admin Orchestrator no encontrados")
    
    admin_agents = get_admin_agents()
    
    # ========== FASE 1: ANÁLISIS Y ESTRATEGIA ==========
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="analyzer",
        node_name="🎯 Analizando estrategia administrativa",
        data={"query": query}
    )
    
    analyzer_prompt = analyzer_node.system_prompt.replace("{{user_query}}", query)
    
    analyzer_messages = build_llm_messages(
        system_prompt=analyzer_prompt,
        template=analyzer_node.prompt_template,
        variables={},
        memory=None
    )
    
    strategy_response = await call_llm(
        llm_url, model, analyzer_messages,
        temperature=analyzer_node.temperature,
        provider_type=provider_type,
        api_key=api_key
    )
    
    strategy_data = extract_json(strategy_response)
    
    if not strategy_data:
        # Estrategia por defecto: delegación directa
        strategy_data = {
            "task_type": "other",
            "complexity": "medium",
            "strategy": "DIRECTA",
            "needs_knowledge": False,
            "execution_plan": [
                {"step": 1, "agent": "persistent_admin", "task": query}
            ],
            "reasoning": "Estrategia por defecto: delegación directa al agente administrativo"
        }
    
    yield StreamEvent(
        event_type="node_end",
        execution_id=execution_id,
        node_id="analyzer",
        node_name="🎯 Estrategia definida",
        data={
            "task_type": strategy_data.get("task_type"),
            "strategy": strategy_data.get("strategy"),
            "reasoning": strategy_data.get("reasoning"),
            "steps_count": len(strategy_data.get("execution_plan", []))
        }
    )
    
    # ========== FASE 2: RECOPILACIÓN DE CONOCIMIENTO (si es necesario) ==========
    knowledge_context = ""
    
    if strategy_data.get("needs_knowledge") and strategy_data.get("knowledge_query"):
        yield StreamEvent(
            event_type="node_start",
            execution_id=execution_id,
            node_id="knowledge_gatherer",
            node_name="📚 Consultando conocimiento previo",
            data={"query": strategy_data.get("knowledge_query")}
        )
        
        knowledge_result = await execute_admin_subagent(
            agent_id="rag",
            task=strategy_data.get("knowledge_query"),
            context="",
            llm_url=llm_url,
            model=model,
            config=config,
            execution_id=execution_id,
            provider_type=provider_type,
            api_key=api_key,
            memory=memory
        )
        
        if knowledge_result.get("success"):
            knowledge_context = knowledge_result.get("response", "")
        
        yield StreamEvent(
            event_type="node_end",
            execution_id=execution_id,
            node_id="knowledge_gatherer",
            node_name="📚 Conocimiento recopilado",
            data={
                "success": knowledge_result.get("success"),
                "context_length": len(knowledge_context)
            }
        )
    
    # ========== FASE 3: EJECUCIÓN DEL PLAN ==========
    execution_plan = strategy_data.get("execution_plan", [])
    steps_results = []
    accumulated_context = knowledge_context
    
    for step in execution_plan:
        step_num = step.get("step", len(steps_results) + 1)
        agent_id = step.get("agent", "persistent_admin")
        task_description = step.get("task", query)
        
        agent_info = admin_agents.get(agent_id, {"name": agent_id})
        
        yield StreamEvent(
            event_type="node_start",
            execution_id=execution_id,
            node_id=f"executor_step_{step_num}",
            node_name=f"⚡ Paso {step_num}: {agent_info.get('name')}",
            data={
                "step": step_num,
                "agent": agent_id,
                "task": task_description
            }
        )
        
        step_result = await execute_admin_subagent(
            agent_id=agent_id,
            task=task_description,
            context=accumulated_context,
            llm_url=llm_url,
            model=model,
            config=config,
            execution_id=execution_id,
            provider_type=provider_type,
            api_key=api_key,
            memory=memory
        )
        
        steps_results.append({
            "step": step_num,
            "agent": agent_id,
            "task": task_description,
            "success": step_result.get("success"),
            "response": step_result.get("response", "")[:1000]  # Truncar para contexto
        })
        
        # Acumular contexto para siguiente paso
        if step_result.get("success"):
            accumulated_context += f"\n\n[Paso {step_num} completado]: {step_result.get('response', '')[:500]}"
        
        yield StreamEvent(
            event_type="node_end",
            execution_id=execution_id,
            node_id=f"executor_step_{step_num}",
            node_name=f"⚡ Paso {step_num} completado",
            data={
                "step": step_num,
                "success": step_result.get("success"),
                "agent": agent_id
            }
        )
        
        # Si un paso falla y es crítico, detener ejecución
        if not step_result.get("success") and agent_id == "persistent_admin":
            logger.warning(f"Paso crítico {step_num} falló, deteniendo ejecución")
            break
    
    # ========== FASE 4: SÍNTESIS FINAL ==========
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="synthesizer",
        node_name="📊 Generando respuesta final",
        data={"total_steps": len(steps_results)}
    )
    
    # Preparar resumen de pasos
    steps_summary = []
    for sr in steps_results:
        steps_summary.append(f"Paso {sr['step']} ({sr['agent']}): {'✅ Éxito' if sr['success'] else '❌ Error'}")
    
    # Obtener resultado final (último paso exitoso)
    final_result = ""
    for sr in reversed(steps_results):
        if sr.get("success"):
            final_result = sr.get("response", "")
            break
    
    synth_prompt = synth_node.system_prompt
    synth_prompt = synth_prompt.replace("{{user_query}}", query)
    synth_prompt = synth_prompt.replace("{{strategy}}", strategy_data.get("strategy", ""))
    synth_prompt = synth_prompt.replace("{{steps_summary}}", "\n".join(steps_summary))
    synth_prompt = synth_prompt.replace("{{final_result}}", final_result[:2000])
    
    synth_messages = build_llm_messages(
        system_prompt=synth_prompt,
        template=synth_node.prompt_template,
        variables={},
        memory=None
    )
    
    full_response = ""
    async for token in call_llm_stream(
        llm_url, model, synth_messages,
        temperature=synth_node.temperature,
        provider_type=provider_type,
        api_key=api_key
    ):
        full_response += token
        yield StreamEvent(
            event_type="token",
            execution_id=execution_id,
            node_id="synthesizer",
            content=token
        )
    
    yield StreamEvent(
        event_type="node_end",
        execution_id=execution_id,
        node_id="synthesizer",
        node_name="📊 Respuesta generada",
        data={
            "strategy": strategy_data.get("strategy"),
            "steps_executed": len(steps_results),
            "success": all(sr.get("success") for sr in steps_results)
        }
    )
    
    # Resultado para modo no-streaming
    if not stream:
        yield {"_result": {
            "response": full_response,
            "strategy": strategy_data,
            "steps_results": steps_results
        }}


# ============================================
# Registro del Agente
# ============================================

def register_admin_orchestrator_agent():
    """Registrar el coordinador administrativo"""
    
    chain_registry.register(
        chain_id="admin_orchestrator",
        definition=ADMIN_ORCHESTRATOR_DEFINITION,
        builder=build_admin_orchestrator_agent
    )
    
    logger.info("Admin Orchestrator Agent registrado (v1.0.0)")
