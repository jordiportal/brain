"""
Orchestrator Agent - REFACTORIZADO con estándar
Agente orquestador con patrón ReAct (Reason + Act).

Descompone tareas complejas en pasos, piensa antes de actuar,
y delega a agentes especializados registrados en el chain_registry.
Soporta múltiples proveedores LLM: Ollama, OpenAI, Anthropic, etc.
"""

import json
import re
from typing import AsyncGenerator, Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ..models import (
    ChainDefinition,
    ChainConfig,
    NodeDefinition,
    NodeType,
    StreamEvent,
    ChainInvokeRequest
)
from ..registry import chain_registry
from .llm_utils import call_llm, call_llm_stream
from .agent_helpers import (  # ✅ Usar helpers compartidos
    extract_json,
    build_llm_messages
)


# ============================================
# Modelos de Datos del Orchestrator
# ============================================

class StepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """Un paso en el plan de ejecución"""
    id: int
    description: str
    agent: str  # ID del agente del registry
    status: StepStatus = StepStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None


@dataclass 
class ExecutionContext:
    """Contexto de ejecución del orquestador"""
    original_query: str
    plan: List[PlanStep] = field(default_factory=list)
    current_step: int = 0
    observations: List[Dict[str, Any]] = field(default_factory=list)
    final_answer: Optional[str] = None
    iteration: int = 0
    max_iterations: int = 10


# ============================================
# Funciones específicas del Orchestrator
# ============================================

def get_available_agents() -> Dict[str, Dict[str, str]]:
    """
    Obtener todos los agentes disponibles del registry,
    excluyendo el propio orquestador.
    """
    agents = {}
    for chain_id in chain_registry.list_chain_ids():
        if chain_id == "orchestrator":
            continue
        
        definition = chain_registry.get(chain_id)
        if definition:
            agents[chain_id] = {
                "name": definition.name,
                "description": definition.description,
                "type": definition.type
            }
    
    return agents


def get_agents_description_for_prompt() -> str:
    """Generar descripción de agentes para el prompt del planificador"""
    agents = get_available_agents()
    
    if not agents:
        return "- conversational: Respuestas generales y conversación"
    
    lines = []
    for agent_id, info in agents.items():
        lines.append(f"- {agent_id}: {info['description']}")
    
    return "\n".join(lines)


def extract_json_from_response(response: str) -> Optional[Dict]:
    """
    Extraer datos JSON de una respuesta de agente.
    Útil para pasar datos estructurados entre agentes.
    """
    json_blocks = re.findall(r'```json\s*([\s\S]*?)\s*```', response)
    
    for block in json_blocks:
        try:
            data = json.loads(block.strip())
            if isinstance(data, (dict, list)) and data:
                return data
        except json.JSONDecodeError:
            continue
    
    # Buscar objetos JSON sueltos
    try:
        import re as re_module
        match = re_module.search(r'\{[\s\S]*\}', response)
        if match:
            return json.loads(match.group())
    except:
        pass
    
    return None


async def execute_sub_agent(
    agent_id: str,
    task: str,
    context: str,
    llm_url: str,
    model: str,
    config: ChainConfig,
    execution_id: str,
    provider_type: str = "ollama",
    api_key: Optional[str] = None,
    previous_result: Optional[Dict[str, Any]] = None,
    memory: Optional[list] = None
) -> Dict[str, Any]:
    """
    Ejecutar un sub-agente del registry y capturar su resultado.
    Pasa los parámetros del proveedor LLM al sub-agente.
    
    Args:
        previous_result: Resultado estructurado del paso anterior (para pasar datos entre agentes)
        memory: Memoria de la conversación a pasar al sub-agente
    """
    builder = chain_registry.get_builder(agent_id)
    definition = chain_registry.get(agent_id)
    
    if not builder or not definition:
        return {
            "success": False,
            "error": f"Agente '{agent_id}' no encontrado en el registry",
            "response": None
        }
    
    try:
        # Preparar input para el sub-agente
        message = task
        
        if context and context != "Ninguna aún":
            message = f"{task}\n\nCONTEXTO PREVIO:\n{context}"
        
        # Si hay datos estructurados del paso anterior (para code_execution_agent)
        if previous_result and agent_id == "code_execution_agent":
            prev_response = previous_result.get("response", "")
            json_data = extract_json_from_response(prev_response)
            
            if json_data:
                message += f"\n\nDATOS DISPONIBLES (JSON):\n```json\n{json.dumps(json_data, indent=2, ensure_ascii=False)}\n```"
        
        sub_input = {
            "message": message,
            "query": message
        }
        
        # Ejecutar el sub-agente (modo no-streaming para capturar resultado)
        result = None
        full_response = ""
        tools_used = []
        sources = []
        raw_data = None
        
        async for event in builder(
            config=definition.config,
            llm_url=llm_url,
            model=model,
            input_data=sub_input,
            memory=memory or [],
            execution_id=f"{execution_id}_sub_{agent_id}",
            stream=False,
            provider_type=provider_type,
            api_key=api_key
        ):
            if isinstance(event, dict) and "_result" in event:
                result = event["_result"]
                full_response = result.get("response", "")
                tools_used = result.get("tools_used", [])
                sources = result.get("sources", [])
                
                # Capturar datos raw para pasar a siguiente agente
                if "tool_results" in result and result["tool_results"]:
                    tool_result = result["tool_results"][0]
                    if "result" in tool_result and "data" in tool_result["result"]:
                        raw_data = tool_result["result"]["data"]
                
                break
            
            if hasattr(event, 'event_type'):
                if event.event_type == "token" and event.content:
                    full_response += event.content
                elif event.event_type == "node_end" and event.data:
                    if "response" in event.data:
                        full_response = event.data["response"]
                    if "tools_used" in event.data:
                        tools_used = event.data["tools_used"]
                    if "sources" in event.data:
                        sources = event.data["sources"]
        
        return {
            "success": True,
            "response": full_response,
            "tools_used": tools_used,
            "sources": sources,
            "agent_name": definition.name,
            "raw_data": raw_data
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "response": None
        }


def select_default_agent(query: str) -> str:
    """Seleccionar agente por defecto basado en keywords"""
    query_lower = query.lower()
    
    sap_keywords = ["sap", "pedido", "venta", "producto", "cliente", "saldo", "banco", "factura", "stock", "inventario"]
    rag_keywords = ["documento", "buscar", "encontrar", "información sobre", "qué dice", "manual", "guía"]
    tool_keywords = ["calcular", "hora", "fecha", "buscar en web", "suma", "resta", "matemátic"]
    
    if any(kw in query_lower for kw in sap_keywords):
        return "sap_agent"
    elif any(kw in query_lower for kw in rag_keywords):
        return "rag"
    elif any(kw in query_lower for kw in tool_keywords):
        return "tool_agent"
    else:
        return "conversational"


# ============================================
# Definición del Agente (con prompts editables)
# ============================================

ORCHESTRATOR_DEFINITION = ChainDefinition(
    id="orchestrator",
    name="Orchestrator Agent",
    description="Agente orquestador que descompone tareas complejas en pasos y delega a agentes especializados del registry (SAP Agent, RAG, Tool Agent, Conversational).",
    type="agent",
    version="3.0.0",  # ✅ Versión actualizada con estándar
    nodes=[
        NodeDefinition(
            id="input",
            type=NodeType.INPUT,
            name="Petición"
        ),
        NodeDefinition(
            id="planner",
            type=NodeType.LLM,
            name="Planificador",
            # ✅ System prompt editable con variables
            system_prompt="""Eres un planificador experto. Tu tarea es analizar la petición del usuario y crear un plan de pasos concretos.

AGENTES DISPONIBLES:
{{agents_description}}

PETICIÓN DEL USUARIO:
{{user_query}}

INSTRUCCIONES:
1. Analiza qué información necesita el usuario
2. Descompón la tarea en pasos simples y concretos
3. Asigna el agente apropiado a cada paso (usa el ID exacto del agente)
4. Responde SOLO con JSON en este formato:

```json
{
  "analysis": "Breve análisis de la petición",
  "plan": [
    {"step": 1, "description": "Descripción del paso", "agent": "agent_id"},
    {"step": 2, "description": "Descripción del paso", "agent": "agent_id"}
  ]
}
```

REGLAS:
- Si la petición es simple, usa un solo paso
- Máximo 5 pasos
- Para consultas SAP (pedidos, productos, clientes, saldos, usuarios), usa "sap_agent"
- Para búsqueda en documentos/conocimiento, usa "rag"
- Para cálculos y herramientas básicas, usa "tool_agent"
- Para procesamiento de datos, análisis, gráficos o código, usa "code_execution_agent"
- Para conversación general, usa "conversational"

PATRONES COMUNES DE MULTI-AGENTE:
- "Analiza/estadísticas de datos SAP" → sap_agent + code_execution_agent
- "Busca y resume documentos" → rag + conversational
- "Obtén datos y genera gráfico" → sap_agent/tool_agent + code_execution_agent""",
            prompt_template="Crea el plan de ejecución.",
            temperature=0.2
        ),
        NodeDefinition(
            id="thinker",
            type=NodeType.LLM,
            name="Pensador ReAct",
            # ✅ System prompt editable
            system_prompt="""Eres un agente que piensa cuidadosamente antes de actuar.

CONTEXTO:
- Petición original: {{original_query}}
- Plan actual: {{plan}}
- Paso actual: {{current_step}}
- Observaciones anteriores: {{observations}}

INSTRUCCIONES:
Piensa en voz alta sobre:
1. Qué información tienes hasta ahora
2. Qué necesitas hacer en este paso
3. Cómo vas a proceder

Responde con tu razonamiento en 2-3 oraciones.""",
            prompt_template="¿Qué piensas sobre este paso?",
            temperature=0.3
        ),
        NodeDefinition(
            id="react_loop",
            type=NodeType.TOOL,
            name="Bucle ReAct (Delegación)"
        ),
        NodeDefinition(
            id="observer",
            type=NodeType.LLM,
            name="Observador",
            # ✅ System prompt editable
            system_prompt="""Analiza el resultado de la acción ejecutada.

PASO EJECUTADO: {{step_description}}
AGENTE USADO: {{agent_id}}
RESULTADO OBTENIDO:
```
{{result}}
```

INSTRUCCIONES:
1. Resume los datos clave obtenidos (máximo 3 puntos)
2. Indica si el paso fue exitoso
3. Menciona información relevante para los siguientes pasos

Responde de forma concisa.""",
            prompt_template="Analiza el resultado.",
            temperature=0.3
        ),
        NodeDefinition(
            id="synthesizer",
            type=NodeType.LLM,
            name="Sintetizador",
            # ✅ System prompt editable
            system_prompt="""Genera la respuesta final para el usuario basándote en toda la información recopilada.

PETICIÓN ORIGINAL:
{{original_query}}

PLAN EJECUTADO:
{{plan}}

OBSERVACIONES DE CADA PASO:
{{observations}}

INSTRUCCIONES:
- Responde directamente a la petición del usuario
- Usa los datos obtenidos para dar una respuesta completa
- Si hay tablas o listas, formatea con markdown
- Si hubo errores, menciónalos
- Sé conciso pero completo
- Responde en español""",
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
        temperature=0.5,
        use_memory=True,
        max_memory_messages=20
    )
)


# ============================================
# Builder Function (Lógica del Agente)
# ============================================

async def build_orchestrator_agent(
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
    Builder del agente orquestador con patrón ReAct.
    
    FASES:
    1. Planning: Analizar query y crear plan de pasos
    2. ReAct Loop: Para cada paso:
       - Think: Razonar sobre el paso
       - Act: Delegar a sub-agente
       - Observe: Analizar resultado
    3. Synthesis: Generar respuesta final
    
    NODOS:
    - input (INPUT): Petición del usuario
    - planner (LLM): Crea plan de ejecución
    - thinker (LLM): Razona antes de cada paso
    - react_loop (TOOL): Delega a sub-agentes
    - observer (LLM): Analiza resultado de cada paso
    - synthesizer (LLM): Genera respuesta final
    - output (OUTPUT): Respuesta completa
    
    MEMORY: Yes (hasta 20 mensajes) - Compartida con sub-agentes
    TOOLS: Todos los agentes registrados en chain_registry
    """
    
    query = input_data.get("message", input_data.get("query", ""))
    max_iterations = input_data.get("max_steps", 10)
    
    ctx = ExecutionContext(
        original_query=query,
        max_iterations=max_iterations
    )
    
    # ✅ Obtener nodos con prompts editables
    planner_node = ORCHESTRATOR_DEFINITION.get_node("planner")
    thinker_node = ORCHESTRATOR_DEFINITION.get_node("thinker")
    observer_node = ORCHESTRATOR_DEFINITION.get_node("observer")
    synth_node = ORCHESTRATOR_DEFINITION.get_node("synthesizer")
    
    if not all([planner_node, thinker_node, observer_node, synth_node]):
        raise ValueError("Nodos del Orchestrator no encontrados")
    
    available_agents = get_available_agents()
    agents_desc = get_agents_description_for_prompt()
    
    # ========== FASE 1: PLANIFICACIÓN ==========
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="planner",
        node_name="📋 Planificador",
        data={
            "phase": "planning", 
            "query": query,
            "available_agents": list(available_agents.keys())
        }
    )
    
    # ✅ Reemplazar variables en planner prompt
    planner_prompt = planner_node.system_prompt
    planner_prompt = planner_prompt.replace("{{agents_description}}", agents_desc)
    planner_prompt = planner_prompt.replace("{{user_query}}", query)
    
    # ✅ Usar helper para construir mensajes
    planner_messages = build_llm_messages(
        system_prompt=planner_prompt,
        template=planner_node.prompt_template,
        variables={},
        memory=memory,
        max_memory=10
    )
    
    plan_response = await call_llm(
        llm_url, model, planner_messages,
        temperature=planner_node.temperature,
        provider_type=provider_type,
        api_key=api_key
    )
    
    plan_data = extract_json(plan_response)  # ✅ Usar helper compartido
    
    if plan_data and "plan" in plan_data:
        for step in plan_data["plan"]:
            agent_id = step.get("agent", "conversational")
            if agent_id not in available_agents and agent_id != "conversational":
                agent_id = select_default_agent(step.get("description", ""))
            
            ctx.plan.append(PlanStep(
                id=step.get("step", len(ctx.plan) + 1),
                description=step.get("description", ""),
                agent=agent_id
            ))
        analysis = plan_data.get("analysis", "")
    else:
        # Plan por defecto
        default_agent = select_default_agent(query)
        ctx.plan.append(PlanStep(
            id=1,
            description=query,
            agent=default_agent
        ))
        analysis = f"Ejecutando como tarea simple con {default_agent}"
    
    yield StreamEvent(
        event_type="node_end",
        execution_id=execution_id,
        node_id="planner",
        node_name="📋 Planificador",
        data={
            "analysis": analysis,
            "plan": [{"step": s.id, "description": s.description, "agent": s.agent} for s in ctx.plan]
        }
    )
    
    # ========== FASE 2: BUCLE REACT ==========
    while ctx.current_step < len(ctx.plan) and ctx.iteration < ctx.max_iterations:
        ctx.iteration += 1
        step = ctx.plan[ctx.current_step]
        step.status = StepStatus.IN_PROGRESS
        
        # ----- THINK -----
        yield StreamEvent(
            event_type="node_start",
            execution_id=execution_id,
            node_id=f"think_{ctx.current_step}",
            node_name=f"🧠 Pensando (Paso {step.id})",
            data={"step": step.id, "description": step.description, "agent": step.agent}
        )
        
        # ✅ Reemplazar variables en thinker prompt
        think_prompt = thinker_node.system_prompt
        think_prompt = think_prompt.replace("{{original_query}}", ctx.original_query)
        think_prompt = think_prompt.replace("{{plan}}", json.dumps([{"step": s.id, "desc": s.description, "agent": s.agent, "status": s.status.value} for s in ctx.plan], ensure_ascii=False))
        think_prompt = think_prompt.replace("{{current_step}}", f"Paso {step.id}: {step.description} (usando agente: {step.agent})")
        think_prompt = think_prompt.replace("{{observations}}", json.dumps(ctx.observations[-3:], ensure_ascii=False, default=str) if ctx.observations else "Ninguna aún")
        
        think_messages = build_llm_messages(
            system_prompt=think_prompt,
            template=thinker_node.prompt_template,
            variables={},
            memory=None
        )
        
        thinking = await call_llm(
            llm_url, model, think_messages,
            temperature=thinker_node.temperature,
            provider_type=provider_type,
            api_key=api_key
        )
        
        yield StreamEvent(
            event_type="node_end",
            execution_id=execution_id,
            node_id=f"think_{ctx.current_step}",
            node_name=f"🧠 Pensando (Paso {step.id})",
            data={"thinking": thinking}
        )
        
        # ----- ACT: Delegar al sub-agente -----
        agent_info = available_agents.get(step.agent, {"name": step.agent})
        
        yield StreamEvent(
            event_type="node_start",
            execution_id=execution_id,
            node_id=f"act_{ctx.current_step}",
            node_name=f"⚡ Delegando a {agent_info.get('name', step.agent)} (Paso {step.id})",
            data={"agent": step.agent, "task": step.description}
        )
        
        prev_context = json.dumps(ctx.observations[-2:], ensure_ascii=False, default=str) if ctx.observations else ""
        previous_result = ctx.observations[-1] if ctx.observations else None
        
        action_result = await execute_sub_agent(
            agent_id=step.agent,
            task=step.description,
            context=prev_context,
            llm_url=llm_url,
            model=model,
            config=config,
            execution_id=execution_id,
            provider_type=provider_type,
            api_key=api_key,
            previous_result=previous_result,
            memory=memory
        )
        
        if action_result.get("success"):
            step.status = StepStatus.COMPLETED
            step.result = action_result.get("response", "")[:2000]
        else:
            step.status = StepStatus.FAILED
            step.error = action_result.get("error", "Error desconocido")
        
        yield StreamEvent(
            event_type="node_end",
            execution_id=execution_id,
            node_id=f"act_{ctx.current_step}",
            node_name=f"⚡ Delegando a {agent_info.get('name', step.agent)} (Paso {step.id})",
            data={
                "status": step.status.value,
                "agent_used": step.agent,
                "tools_used": action_result.get("tools_used", []),
                "sources": action_result.get("sources", []),
                "result_preview": str(action_result.get("response", ""))[:500]
            }
        )
        
        # ----- OBSERVE -----
        yield StreamEvent(
            event_type="node_start",
            execution_id=execution_id,
            node_id=f"observe_{ctx.current_step}",
            node_name=f"👁 Observando (Paso {step.id})",
            data={}
        )
        
        # ✅ Reemplazar variables en observer prompt
        observe_prompt = observer_node.system_prompt
        observe_prompt = observe_prompt.replace("{{step_description}}", step.description)
        observe_prompt = observe_prompt.replace("{{agent_id}}", step.agent)
        observe_prompt = observe_prompt.replace("{{result}}", json.dumps(action_result, ensure_ascii=False, default=str)[:3000])
        
        observe_messages = build_llm_messages(
            system_prompt=observe_prompt,
            template=observer_node.prompt_template,
            variables={},
            memory=None
        )
        
        observation = await call_llm(
            llm_url, model, observe_messages,
            temperature=observer_node.temperature,
            provider_type=provider_type,
            api_key=api_key
        )
        
        ctx.observations.append({
            "step": step.id,
            "description": step.description,
            "agent": step.agent,
            "observation": observation,
            "raw_result": action_result
        })
        
        yield StreamEvent(
            event_type="node_end",
            execution_id=execution_id,
            node_id=f"observe_{ctx.current_step}",
            node_name=f"👁 Observando (Paso {step.id})",
            data={"observation": observation}
        )
        
        ctx.current_step += 1
    
    # ========== FASE 3: SÍNTESIS FINAL ==========
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="synthesizer",
        node_name="📝 Generando respuesta final",
        data={
            "total_steps": len(ctx.plan), 
            "iterations": ctx.iteration,
            "agents_used": list(set(s.agent for s in ctx.plan))
        }
    )
    
    # ✅ Reemplazar variables en synthesizer prompt
    synth_prompt = synth_node.system_prompt
    synth_prompt = synth_prompt.replace("{{original_query}}", ctx.original_query)
    synth_prompt = synth_prompt.replace("{{plan}}", json.dumps([{
        "paso": s.id, 
        "descripción": s.description, 
        "agente": s.agent,
        "estado": s.status.value
    } for s in ctx.plan], ensure_ascii=False))
    synth_prompt = synth_prompt.replace("{{observations}}", json.dumps([{
        "paso": o["step"], 
        "agente": o["agent"],
        "observación": o["observation"]
    } for o in ctx.observations], ensure_ascii=False, default=str))
    
    synth_messages = build_llm_messages(
        system_prompt=synth_prompt,
        template=synth_node.prompt_template,
        variables={},
        memory=memory,
        max_memory=10
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
    
    ctx.final_answer = full_response
    
    yield StreamEvent(
        event_type="node_end",
        execution_id=execution_id,
        node_id="synthesizer",
        node_name="📝 Generando respuesta final",
        data={
            "response": full_response[:500],
            "total_iterations": ctx.iteration,
            "steps_completed": sum(1 for s in ctx.plan if s.status == StepStatus.COMPLETED),
            "agents_used": list(set(s.agent for s in ctx.plan))
        }
    )
    
    # Resultado para modo no-streaming
    if not stream:
        yield {"_result": {
            "response": full_response,
            "plan": [{
                "step": s.id, 
                "description": s.description, 
                "agent": s.agent,
                "status": s.status.value
            } for s in ctx.plan],
            "observations": ctx.observations,
            "iterations": ctx.iteration,
            "agents_used": list(set(s.agent for s in ctx.plan))
        }}


# ============================================
# Registro del Agente
# ============================================

def register_orchestrator_agent():
    """Registrar el agente orquestador"""
    
    chain_registry.register(
        chain_id="orchestrator",
        definition=ORCHESTRATOR_DEFINITION,
        builder=build_orchestrator_agent
    )
