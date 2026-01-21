"""
Orchestrator Agent - Agente orquestador con patrón ReAct (Reason + Act)

Descompone tareas complejas en pasos, piensa antes de actuar,
y delega a agentes especializados REGISTRADOS en el chain_registry.
Soporta múltiples proveedores LLM: Ollama, OpenAI, Anthropic, etc.
"""

import json
import re
from typing import AsyncGenerator, Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ..models import ChainConfig, StreamEvent, ChainInvokeRequest
from ..registry import chain_registry
from .llm_utils import call_llm, call_llm_stream


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
# Funciones para obtener agentes del Registry
# ============================================

def get_available_agents() -> Dict[str, Dict[str, str]]:
    """
    Obtener todos los agentes disponibles del registry,
    excluyendo el propio orquestador.
    """
    agents = {}
    for chain_id in chain_registry.list_chain_ids():
        # Excluir el orquestador de la lista
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
    """
    Generar descripción de agentes para el prompt del planificador.
    """
    agents = get_available_agents()
    
    if not agents:
        return "- conversational: Respuestas generales y conversación"
    
    lines = []
    for agent_id, info in agents.items():
        lines.append(f"- {agent_id}: {info['description']}")
    
    return "\n".join(lines)


# ============================================
# Prompts del Orquestador
# ============================================

def get_planner_prompt(query: str) -> str:
    """Generar el prompt del planificador con agentes dinámicos"""
    agents_desc = get_agents_description_for_prompt()
    
    return f"""Eres un planificador experto. Tu tarea es analizar la petición del usuario y crear un plan de pasos concretos.

AGENTES DISPONIBLES:
{agents_desc}

PETICIÓN DEL USUARIO:
{query}

INSTRUCCIONES:
1. Analiza qué información necesita el usuario
2. Descompón la tarea en pasos simples y concretos
3. Asigna el agente apropiado a cada paso (usa el ID exacto del agente)
4. Responde SOLO con JSON en este formato:

```json
{{
  "analysis": "Breve análisis de la petición",
  "plan": [
    {{"step": 1, "description": "Descripción del paso", "agent": "agent_id"}},
    {{"step": 2, "description": "Descripción del paso", "agent": "agent_id"}}
  ]
}}
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
- "Obtén datos y genera gráfico" → sap_agent/tool_agent + code_execution_agent
"""


THINKER_PROMPT = """Eres un agente que piensa cuidadosamente antes de actuar.

CONTEXTO:
- Petición original: {original_query}
- Plan actual: {plan}
- Paso actual: {current_step}
- Observaciones anteriores: {observations}

INSTRUCCIONES:
Piensa en voz alta sobre:
1. Qué información tienes hasta ahora
2. Qué necesitas hacer en este paso
3. Cómo vas a proceder

Responde con tu razonamiento en 2-3 oraciones."""


OBSERVER_PROMPT = """Analiza el resultado de la acción ejecutada.

PASO EJECUTADO: {step_description}
AGENTE USADO: {agent_id}
RESULTADO OBTENIDO:
```
{result}
```

INSTRUCCIONES:
1. Resume los datos clave obtenidos (máximo 3 puntos)
2. Indica si el paso fue exitoso
3. Menciona información relevante para los siguientes pasos

Responde de forma concisa."""


SYNTHESIZER_PROMPT = """Genera la respuesta final para el usuario basándote en toda la información recopilada.

PETICIÓN ORIGINAL:
{original_query}

PLAN EJECUTADO:
{plan}

OBSERVACIONES DE CADA PASO:
{observations}

INSTRUCCIONES:
- Responde directamente a la petición del usuario
- Usa los datos obtenidos para dar una respuesta completa
- Si hay tablas o listas, formatea con markdown
- Si hubo errores, menciónalos
- Sé conciso pero completo
- Responde en español"""


# ============================================
# Funciones auxiliares
# ============================================

def extract_json(text: str) -> Optional[Dict]:
    """Extraer JSON de un texto"""
    patterns = [
        r'```json\s*([\s\S]*?)\s*```',
        r'```\s*([\s\S]*?)\s*```',
        r'\{[\s\S]*\}'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue
    
    try:
        return json.loads(text.strip())
    except:
        return None


def extract_json_from_response(response: str) -> Optional[Dict]:
    """
    Extraer datos JSON de una respuesta de agente.
    Útil para pasar datos estructurados entre agentes.
    """
    # Intentar extraer bloques JSON del markdown
    json_blocks = re.findall(r'```json\s*([\s\S]*?)\s*```', response)
    
    for block in json_blocks:
        try:
            data = json.loads(block.strip())
            # Si tiene estructura de datos útiles, devolverlo
            if isinstance(data, (dict, list)) and data:
                return data
        except json.JSONDecodeError:
            continue
    
    # Buscar objetos JSON sueltos
    try:
        # Buscar el primer objeto JSON válido
        match = re.search(r'\{[\s\S]*\}', response)
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
    # Obtener el builder del agente
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
        
        # Si hay contexto de pasos anteriores, agregarlo
        if context and context != "Ninguna aún":
            message = f"{task}\n\nCONTEXTO PREVIO:\n{context}"
        
        # Si hay datos estructurados del paso anterior (para code_execution_agent)
        if previous_result and agent_id == "code_execution_agent":
            # Extraer datos JSON del resultado anterior
            prev_response = previous_result.get("response", "")
            
            # Intentar extraer JSON del resultado anterior
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
        raw_data = None  # Para capturar datos estructurados
        
        async for event in builder(
            config=definition.config,  # Usar config del agente
            llm_url=llm_url,
            model=model,
            input_data=sub_input,
            memory=memory or [],  # Pasar memoria del orchestrator a sub-agente
            execution_id=f"{execution_id}_sub_{agent_id}",
            stream=False,  # No streaming para sub-agentes
            provider_type=provider_type,
            api_key=api_key
        ):
            # Capturar resultado final
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
            
            # Si es StreamEvent con tokens, acumular
            if hasattr(event, 'event_type'):
                if event.event_type == "token" and event.content:
                    full_response += event.content
                elif event.event_type == "node_end" and event.data:
                    # Capturar respuesta de eventos de fin
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
            "raw_data": raw_data  # Datos estructurados para siguiente agente
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "response": None
        }


def select_default_agent(query: str) -> str:
    """
    Seleccionar agente por defecto basado en keywords.
    """
    query_lower = query.lower()
    
    # Keywords para cada agente
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
# Builder del Orquestador
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
):
    """
    Builder del agente orquestador con patrón ReAct.
    
    Delega la ejecución a agentes registrados en el chain_registry.
    Soporta múltiples proveedores LLM.
    """
    
    query = input_data.get("message", input_data.get("query", ""))
    max_iterations = input_data.get("max_steps", 10)
    
    ctx = ExecutionContext(
        original_query=query,
        max_iterations=max_iterations
    )
    
    # Log de agentes disponibles
    available_agents = get_available_agents()
    
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
    
    planner_prompt = get_planner_prompt(query)
    planner_messages = [
        {"role": "system", "content": planner_prompt}
    ]
    
    # Agregar memoria si existe (conversación previa)
    if memory:
        planner_messages.extend(memory[-10:])  # Últimos 10 mensajes
    
    planner_messages.append({"role": "user", "content": "Crea el plan de ejecución."})
    
    plan_response = await call_llm(llm_url, model, planner_messages, temperature=0.2, provider_type=provider_type, api_key=api_key)
    plan_data = extract_json(plan_response)
    
    if plan_data and "plan" in plan_data:
        for step in plan_data["plan"]:
            agent_id = step.get("agent", "conversational")
            # Validar que el agente existe
            if agent_id not in available_agents and agent_id != "conversational":
                agent_id = select_default_agent(step.get("description", ""))
            
            ctx.plan.append(PlanStep(
                id=step.get("step", len(ctx.plan) + 1),
                description=step.get("description", ""),
                agent=agent_id
            ))
        analysis = plan_data.get("analysis", "")
    else:
        # Plan por defecto si no se pudo parsear
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
        
        think_messages = [
            {"role": "system", "content": THINKER_PROMPT.format(
                original_query=ctx.original_query,
                plan=json.dumps([{"step": s.id, "desc": s.description, "agent": s.agent, "status": s.status.value} for s in ctx.plan], ensure_ascii=False),
                current_step=f"Paso {step.id}: {step.description} (usando agente: {step.agent})",
                observations=json.dumps(ctx.observations[-3:], ensure_ascii=False, default=str) if ctx.observations else "Ninguna aún"
            )},
            {"role": "user", "content": "¿Qué piensas sobre este paso?"}
        ]
        
        thinking = await call_llm(llm_url, model, think_messages, temperature=0.3, provider_type=provider_type, api_key=api_key)
        
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
        
        # Preparar contexto de pasos anteriores
        prev_context = json.dumps(ctx.observations[-2:], ensure_ascii=False, default=str) if ctx.observations else ""
        
        # Obtener resultado del paso anterior para pasar datos estructurados
        previous_result = ctx.observations[-1] if ctx.observations else None
        
        # Ejecutar el sub-agente
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
            previous_result=previous_result,  # Pasar resultado anterior
            memory=memory  # Pasar memoria del orchestrator
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
        
        observe_messages = [
            {"role": "system", "content": OBSERVER_PROMPT.format(
                step_description=step.description,
                agent_id=step.agent,
                result=json.dumps(action_result, ensure_ascii=False, default=str)[:3000]
            )},
            {"role": "user", "content": "Analiza el resultado."}
        ]
        
        observation = await call_llm(llm_url, model, observe_messages, temperature=0.3, provider_type=provider_type, api_key=api_key)
        
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
        
        # Avanzar al siguiente paso
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
    
    synth_messages = [
        {"role": "system", "content": SYNTHESIZER_PROMPT.format(
            original_query=ctx.original_query,
            plan=json.dumps([{
                "paso": s.id, 
                "descripción": s.description, 
                "agente": s.agent,
                "estado": s.status.value
            } for s in ctx.plan], ensure_ascii=False),
            observations=json.dumps([{
                "paso": o["step"], 
                "agente": o["agent"],
                "observación": o["observation"]
            } for o in ctx.observations], ensure_ascii=False, default=str)
        )}
    ]
    
    # Agregar memoria al sintetizador para mantener contexto
    if memory:
        synth_messages.extend(memory[-10:])  # Últimos 10 mensajes
    
    synth_messages.append({"role": "user", "content": "Genera la respuesta final."})
    
    full_response = ""
    async for token in call_llm_stream(llm_url, model, synth_messages, temperature=config.temperature, provider_type=provider_type, api_key=api_key):
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


def register_orchestrator_agent():
    """Registrar el agente orquestador"""
    from ..models import ChainDefinition, NodeDefinition, NodeType, ChainConfig
    
    definition = ChainDefinition(
        id="orchestrator",
        name="Orchestrator Agent",
        description="Agente orquestador que descompone tareas complejas en pasos y delega a agentes especializados del registry (SAP Agent, RAG, Tool Agent, Conversational).",
        type="agent",
        version="2.0.0",  # Nueva versión con delegación
        nodes=[
            NodeDefinition(id="input", type=NodeType.INPUT, name="Petición"),
            NodeDefinition(id="planner", type=NodeType.LLM, name="Planificador"),
            NodeDefinition(id="react_loop", type=NodeType.TOOL, name="Bucle ReAct (Delegación)"),
            NodeDefinition(id="synthesizer", type=NodeType.LLM, name="Sintetizador"),
            NodeDefinition(id="output", type=NodeType.OUTPUT, name="Respuesta")
        ],
        config=ChainConfig(
            temperature=0.5,
            use_memory=True,
            max_memory_messages=20
        )
    )
    
    chain_registry.register(
        chain_id="orchestrator",
        definition=definition,
        builder=build_orchestrator_agent
    )
