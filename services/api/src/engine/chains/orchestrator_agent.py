"""
Orchestrator Agent - Agente orquestador con patrón ReAct (Reason + Act)

Descompone tareas complejas en pasos, piensa antes de actuar,
y delega a agentes especializados.
"""

import json
import re
from typing import AsyncGenerator, Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import httpx
from datetime import datetime

from ..models import ChainConfig, StreamEvent
from ..registry import chain_registry
from ...tools import openapi_toolkit


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
    agent: str  # sap, rag, general
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
# Prompts del Orquestador
# ============================================

PLANNER_PROMPT = """Eres un planificador experto. Tu tarea es analizar la petición del usuario y crear un plan de pasos concretos.

AGENTES DISPONIBLES:
- sap: Consultas a SAP (pedidos, productos, clientes, saldos, bancos)
- general: Análisis, cálculos, comparaciones, razonamiento general

PETICIÓN DEL USUARIO:
{query}

INSTRUCCIONES:
1. Analiza qué información necesita el usuario
2. Descompón la tarea en pasos simples y concretos
3. Asigna el agente apropiado a cada paso
4. Responde SOLO con JSON en este formato:

```json
{{
  "analysis": "Breve análisis de la petición",
  "plan": [
    {{"step": 1, "description": "Descripción del paso", "agent": "sap"}},
    {{"step": 2, "description": "Descripción del paso", "agent": "general"}}
  ]
}}
```

Si la petición es simple y no requiere planificación, responde con un solo paso.
Máximo 5 pasos."""


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


SAP_TOOL_SELECTOR_PROMPT = """Eres un experto en SAP. Debes seleccionar la herramienta correcta para la tarea.

HERRAMIENTAS SAP DISPONIBLES:
{tools}

TAREA A REALIZAR:
{task}

CONTEXTO PREVIO:
{context}

REGLAS IMPORTANTES:
1. Para LISTAR múltiples registros, usa herramientas SIN parámetros obligatorios en la ruta (sin _salesOrder, _id, etc.)
2. Para OBTENER UN REGISTRO ESPECÍFICO, usa herramientas CON parámetro en la ruta
3. NO inventes valores para parámetros - usa solo datos del contexto previo
4. Para limitar resultados, usa "limit" o "$top" en parameters

EJEMPLOS:
- "Listar pedidos de venta" → tool: "sap_btp_gateway_get_api_sales-orders", parameters: {{"limit": 10}}
- "Ver pedido 12345" → tool: "sap_btp_gateway_get_api_sales-orders_salesOrder", parameters: {{"salesOrder": "12345"}}
- "Listar productos" → tool: "sap_btp_gateway_get_api_products", parameters: {{}}

Responde SOLO con JSON:
```json
{{
  "tool": "nombre_exacto_de_la_herramienta",
  "parameters": {{}},
  "reasoning": "Breve explicación"
}}
```"""


OBSERVER_PROMPT = """Analiza el resultado de la acción ejecutada.

PASO EJECUTADO: {step_description}
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

async def ensure_tools_loaded():
    """Asegurar que las herramientas están cargadas"""
    if not openapi_toolkit.tools:
        await openapi_toolkit.load_connections_from_strapi()
        for conn_id in openapi_toolkit.connections:
            try:
                await openapi_toolkit.generate_tools(conn_id)
            except Exception as e:
                print(f"Error cargando tools para {conn_id}: {e}")


async def get_sap_tools_for_prompt() -> str:
    """Obtener lista de herramientas SAP para el prompt"""
    await ensure_tools_loaded()
    
    tools = [t for t in openapi_toolkit.tools.values() 
             if t.id.startswith("sap_btp_gateway")][:25]
    
    lines = []
    for t in tools:
        params = ", ".join([p.get("name", "") for p in t.parameters[:3]])
        lines.append(f"- {t.id}: {t.description[:80]}... [{params}]")
    
    return "\n".join(lines)


async def call_llm(llm_url: str, model: str, messages: List[Dict], temperature: float = 0.3) -> str:
    """Llamar al LLM y obtener respuesta"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{llm_url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": temperature}
            }
        )
        data = response.json()
        return data.get("message", {}).get("content", "")


async def call_llm_stream(llm_url: str, model: str, messages: List[Dict], temperature: float = 0.5):
    """Llamar al LLM con streaming"""
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream(
            "POST",
            f"{llm_url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": True,
                "options": {"temperature": temperature}
            }
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue


def extract_json(text: str) -> Optional[Dict]:
    """Extraer JSON de un texto"""
    # Buscar bloques de código JSON
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
    
    # Intentar parsear todo el texto
    try:
        return json.loads(text.strip())
    except:
        return None


async def execute_sap_tool(tool_id: str, parameters: dict) -> Dict[str, Any]:
    """Ejecutar herramienta SAP"""
    await ensure_tools_loaded()
    
    tool = openapi_toolkit.get_tool(tool_id)
    if not tool:
        return {"error": f"Herramienta no encontrada: {tool_id}", "success": False}
    
    return await tool.execute(**parameters)


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
    **kwargs
):
    """Builder del agente orquestador con patrón ReAct"""
    
    query = input_data.get("message", input_data.get("query", ""))
    max_iterations = input_data.get("max_steps", 10)
    
    ctx = ExecutionContext(
        original_query=query,
        max_iterations=max_iterations
    )
    
    # ========== FASE 1: PLANIFICACIÓN ==========
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="planner",
        node_name="📋 Planificador",
        data={"phase": "planning", "query": query}
    )
    
    planner_messages = [
        {"role": "system", "content": PLANNER_PROMPT.format(query=query)},
        {"role": "user", "content": "Crea el plan de ejecución."}
    ]
    
    plan_response = await call_llm(llm_url, model, planner_messages, temperature=0.2)
    plan_data = extract_json(plan_response)
    
    if plan_data and "plan" in plan_data:
        for step in plan_data["plan"]:
            ctx.plan.append(PlanStep(
                id=step.get("step", len(ctx.plan) + 1),
                description=step.get("description", ""),
                agent=step.get("agent", "general")
            ))
        analysis = plan_data.get("analysis", "")
    else:
        # Plan por defecto si no se pudo parsear
        ctx.plan.append(PlanStep(
            id=1,
            description=query,
            agent="sap" if any(kw in query.lower() for kw in ["sap", "pedido", "venta", "producto", "cliente", "saldo"]) else "general"
        ))
        analysis = "Ejecutando como tarea simple"
    
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
            data={"step": step.id, "description": step.description}
        )
        
        think_messages = [
            {"role": "system", "content": THINKER_PROMPT.format(
                original_query=ctx.original_query,
                plan=json.dumps([{"step": s.id, "desc": s.description, "status": s.status.value} for s in ctx.plan], ensure_ascii=False),
                current_step=f"Paso {step.id}: {step.description}",
                observations=json.dumps(ctx.observations[-3:], ensure_ascii=False, default=str) if ctx.observations else "Ninguna aún"
            )},
            {"role": "user", "content": "¿Qué piensas sobre este paso?"}
        ]
        
        thinking = await call_llm(llm_url, model, think_messages, temperature=0.3)
        
        yield StreamEvent(
            event_type="node_end",
            execution_id=execution_id,
            node_id=f"think_{ctx.current_step}",
            node_name=f"🧠 Pensando (Paso {step.id})",
            data={"thinking": thinking}
        )
        
        # ----- ACT -----
        yield StreamEvent(
            event_type="node_start",
            execution_id=execution_id,
            node_id=f"act_{ctx.current_step}",
            node_name=f"⚡ Actuando (Paso {step.id})",
            data={"agent": step.agent, "task": step.description}
        )
        
        action_result = None
        
        if step.agent == "sap":
            # Seleccionar herramienta SAP
            tools_list = await get_sap_tools_for_prompt()
            
            # Debug
            print(f"[DEBUG] Tools disponibles: {len(tools_list.split(chr(10)))}", flush=True)
            
            selector_messages = [
                {"role": "system", "content": SAP_TOOL_SELECTOR_PROMPT.format(
                    tools=tools_list,
                    task=step.description,
                    context=json.dumps(ctx.observations[-2:], ensure_ascii=False, default=str) if ctx.observations else "Sin contexto previo"
                )},
                {"role": "user", "content": "Selecciona la herramienta."}
            ]
            
            selector_response = await call_llm(llm_url, model, selector_messages, temperature=0.1)
            print(f"[DEBUG] Selector response: {selector_response[:300]}", flush=True)
            
            tool_selection = extract_json(selector_response)
            print(f"[DEBUG] Tool selection: {tool_selection}", flush=True)
            
            if tool_selection and tool_selection.get("tool"):
                tool_id = tool_selection["tool"]
                parameters = tool_selection.get("parameters", {})
                
                yield StreamEvent(
                    event_type="token",
                    execution_id=execution_id,
                    node_id=f"act_{ctx.current_step}",
                    content=f"Ejecutando: {tool_id}\n"
                )
                
                action_result = await execute_sap_tool(tool_id, parameters)
                
                if action_result.get("success"):
                    step.status = StepStatus.COMPLETED
                    step.result = json.dumps(action_result.get("data", {}), ensure_ascii=False, default=str)[:2000]
                else:
                    step.status = StepStatus.FAILED
                    step.error = action_result.get("error", "Error desconocido")
            else:
                step.status = StepStatus.FAILED
                step.error = "No se pudo seleccionar herramienta SAP"
                action_result = {"error": step.error}
        
        else:  # agent == "general"
            # Agente general: razonamiento directo
            general_messages = [
                {"role": "system", "content": f"""Eres un asistente analítico. 
Tarea: {step.description}
Contexto previo: {json.dumps(ctx.observations[-3:], ensure_ascii=False, default=str) if ctx.observations else 'Ninguno'}

Realiza la tarea solicitada de forma concisa."""},
                {"role": "user", "content": step.description}
            ]
            
            general_response = await call_llm(llm_url, model, general_messages, temperature=0.5)
            action_result = {"response": general_response, "success": True}
            step.status = StepStatus.COMPLETED
            step.result = general_response
        
        yield StreamEvent(
            event_type="node_end",
            execution_id=execution_id,
            node_id=f"act_{ctx.current_step}",
            node_name=f"⚡ Actuando (Paso {step.id})",
            data={
                "status": step.status.value,
                "result_preview": str(action_result)[:500] if action_result else None
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
                result=json.dumps(action_result, ensure_ascii=False, default=str)[:3000] if action_result else "Sin resultado"
            )},
            {"role": "user", "content": "Analiza el resultado."}
        ]
        
        observation = await call_llm(llm_url, model, observe_messages, temperature=0.3)
        
        ctx.observations.append({
            "step": step.id,
            "description": step.description,
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
        data={"total_steps": len(ctx.plan), "iterations": ctx.iteration}
    )
    
    synth_messages = [
        {"role": "system", "content": SYNTHESIZER_PROMPT.format(
            original_query=ctx.original_query,
            plan=json.dumps([{"paso": s.id, "descripción": s.description, "estado": s.status.value} for s in ctx.plan], ensure_ascii=False),
            observations=json.dumps([{"paso": o["step"], "observación": o["observation"]} for o in ctx.observations], ensure_ascii=False, default=str)
        )},
        {"role": "user", "content": "Genera la respuesta final."}
    ]
    
    full_response = ""
    async for token in call_llm_stream(llm_url, model, synth_messages, temperature=config.temperature):
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
            "steps_completed": sum(1 for s in ctx.plan if s.status == StepStatus.COMPLETED)
        }
    )
    
    # Resultado para modo no-streaming
    if not stream:
        yield {"_result": {
            "response": full_response,
            "plan": [{"step": s.id, "description": s.description, "status": s.status.value} for s in ctx.plan],
            "observations": ctx.observations,
            "iterations": ctx.iteration
        }}


def register_orchestrator_agent():
    """Registrar el agente orquestador"""
    from ..models import ChainDefinition, NodeDefinition, NodeType, ChainConfig
    
    definition = ChainDefinition(
        id="orchestrator",
        name="Orchestrator Agent",
        description="Agente orquestador que descompone tareas complejas en pasos, piensa antes de actuar, y delega a agentes especializados (SAP, RAG, General).",
        type="agent",
        version="1.0.0",
        nodes=[
            NodeDefinition(id="input", type=NodeType.INPUT, name="Petición"),
            NodeDefinition(id="planner", type=NodeType.LLM, name="Planificador"),
            NodeDefinition(id="react_loop", type=NodeType.TOOL, name="Bucle ReAct"),
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
