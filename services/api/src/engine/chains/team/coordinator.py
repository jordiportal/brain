"""
TeamCoordinator - Cadena para trabajo en equipo con consenso.

Selecciona dinámicamente agentes relevantes para una tarea y
coordina el debate hasta alcanzar consenso.
"""

import json
import time
from typing import Dict, List, Any, Optional, AsyncGenerator

import structlog

from ...models import StreamEvent, ChainConfig
from ..agents.base import subagent_registry
from ..agents import register_all_subagents
from .consensus import ConsensusEngine, ConsensusResult
from .prompts import (
    TEAM_SELECTION_PROMPT,
    EXECUTION_PROMPT,
    build_team_selection_messages
)

logger = structlog.get_logger()


def brain_event(event_type: str, **data) -> str:
    """Genera un Brain Event (HTML comment) para Open WebUI."""
    event = {"type": event_type, **data}
    return f'\n<!--BRAIN_EVENT:{json.dumps(event)}-->\n'


class TeamCoordinator:
    """
    Coordinador de equipos de agentes.
    
    Flujo:
    1. Analiza la tarea y selecciona agentes relevantes
    2. Ejecuta proceso de consenso entre el equipo
    3. Combina propuestas y ejecuta con el agente líder
    """
    
    def __init__(self):
        self.consensus_engine = ConsensusEngine(max_rounds=3)
        self._ensure_registry()
    
    def _ensure_registry(self):
        """Asegura que el registry de agentes está inicializado."""
        if not subagent_registry.list_ids():
            register_all_subagents()
    
    async def _select_team(
        self,
        task: str,
        llm_config: Dict[str, Any]
    ) -> List[Any]:
        """
        Selecciona los agentes más relevantes para la tarea.
        
        Usa el LLM para analizar la tarea y mapear a agentes disponibles.
        """
        self._ensure_registry()
        available_agents = subagent_registry.list()
        
        if not available_agents:
            logger.warning("No agents available in registry")
            return []
        
        # Descripción de agentes disponibles
        agents_desc = []
        for agent in available_agents:
            agents_desc.append({
                "id": agent.id,
                "name": agent.name,
                "role": getattr(agent, 'role', 'Especialista'),
                "expertise": getattr(agent, 'expertise', agent.description)
            })
        
        # Usar LLM para selección inteligente
        try:
            from ..llm_utils import call_llm_with_tools
            
            messages = build_team_selection_messages(task, agents_desc)
            
            response = await call_llm_with_tools(
                messages=messages,
                tools=[],
                temperature=0.3,
                **llm_config
            )
            
            # Parsear respuesta para obtener IDs de agentes
            selected_ids = self._parse_selected_agents(response.content, agents_desc)
            
        except Exception as e:
            logger.warning(f"LLM selection failed, using heuristic: {e}")
            selected_ids = self._heuristic_selection(task, agents_desc)
        
        # Obtener agentes seleccionados
        selected = []
        for agent_id in selected_ids:
            agent = subagent_registry.get(agent_id)
            if agent:
                selected.append(agent)
        
        logger.info(f"Selected team: {[a.id for a in selected]}")
        return selected
    
    def _parse_selected_agents(
        self,
        response: str,
        available: List[Dict]
    ) -> List[str]:
        """Parsea la respuesta del LLM para extraer IDs de agentes."""
        selected = []
        response_lower = response.lower()
        
        for agent in available:
            agent_id = agent["id"]
            # Buscar menciones del agente
            if agent_id in response_lower or agent["name"].lower() in response_lower:
                selected.append(agent_id)
        
        # Si no se encontró ninguno, usar heurística
        if not selected:
            return self._heuristic_selection("", available)
        
        return selected
    
    def _heuristic_selection(
        self,
        task: str,
        available: List[Dict]
    ) -> List[str]:
        """Selección heurística basada en palabras clave."""
        task_lower = task.lower()
        selected = []
        
        # Mapeo de palabras clave a agentes
        keyword_map = {
            "slides_agent": ["presentación", "slides", "diapositivas", "powerpoint"],
            "media_agent": ["imagen", "foto", "ilustración", "genera", "dibuja"],
            "communication_agent": ["comunicación", "mensaje", "narrativa", "historia", "storytelling"],
            "analyst_agent": ["datos", "análisis", "estadísticas", "gráfico", "investigación", "busca"]
        }
        
        for agent_id, keywords in keyword_map.items():
            if any(kw in task_lower for kw in keywords):
                if any(a["id"] == agent_id for a in available):
                    selected.append(agent_id)
        
        # Si es una presentación, incluir comunicación y analista si existen
        if "presentación" in task_lower or "slides" in task_lower:
            for extra in ["communication_agent", "analyst_agent"]:
                if extra not in selected and any(a["id"] == extra for a in available):
                    selected.append(extra)
        
        # Si no hay selección, usar todos los disponibles (máximo 3)
        if not selected:
            selected = [a["id"] for a in available[:3]]
        
        return selected
    
    def _summarize_proposal(self, content: Any) -> str:
        """Resume una propuesta para mostrar al usuario."""
        if isinstance(content, str):
            return content[:150] + "..." if len(content) > 150 else content
        
        if isinstance(content, dict):
            # Buscar campos comunes
            if "response" in content:
                resp = content["response"]
                return resp[:150] + "..." if len(resp) > 150 else resp
            if "summary" in content:
                return content["summary"]
            if "recommendation" in content:
                return content["recommendation"][:150]
            
            # Resumen genérico
            keys = list(content.keys())[:3]
            return f"Propuesta con {len(content)} elementos: {', '.join(keys)}"
        
        return str(content)[:150]


async def build_team_coordinator(
    config: ChainConfig,
    llm_url: str,
    model: str,
    input_data: dict,
    memory: list,
    execution_id: str = "",
    stream: bool = True,
    provider_type: str = "ollama",
    api_key: Optional[str] = None,
    emit_brain_events: bool = True,
    **kwargs
) -> AsyncGenerator[StreamEvent, None]:
    """
    Builder del Team Coordinator - compatible con el sistema de cadenas.
    
    Yields:
        StreamEvents con el progreso y resultado del trabajo en equipo
    """
    start_time = time.time()
    coordinator = TeamCoordinator()
    
    # Extraer tarea y contexto
    task = input_data.get("query", "")
    context = "\n".join([f"{m['role']}: {m['content'][:100]}" for m in memory[-3:]]) if memory else ""
    
    # Configuración LLM
    llm_config = {
        "llm_url": llm_url,
        "model": model,
        "provider_type": provider_type,
        "api_key": api_key
    }
    coordinator.consensus_engine.llm_config = llm_config
    
    response_parts = []
    
    # ========== FASE 1: SELECCIÓN DE EQUIPO ==========
    
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="team_selection",
        node_name="Selección de equipo",
        data={"task": task[:100]}
    )
    
    # Brain Event para Open WebUI
    if emit_brain_events:
        response_parts.append(brain_event("team", action="analyzing", task=task[:100]))
    
    selected_agents = await coordinator._select_team(task, llm_config)
    
    yield StreamEvent(
        event_type="node_end",
        execution_id=execution_id,
        node_id="team_selection",
        data={"agents_selected": len(selected_agents)}
    )
    
    if emit_brain_events:
        response_parts.append(brain_event(
            "team",
            action="selected",
            agents=[{"id": a.id, "name": a.name, "role": getattr(a, 'role', 'Agente')} for a in selected_agents]
        ))
    
    if not selected_agents:
        error_msg = "No se pudieron seleccionar agentes para esta tarea."
        yield StreamEvent(event_type="token", execution_id=execution_id, data={"token": error_msg})
        yield StreamEvent(event_type="end", execution_id=execution_id, data={"output": {"response": error_msg}})
        return
    
    # Mostrar equipo
    team_msg = "\n**Equipo seleccionado:**\n"
    for agent in selected_agents:
        team_msg += f"- {getattr(agent, 'role', 'Agente')}: {agent.name}\n"
    team_msg += "\n"
    
    response_parts.append(team_msg)
    yield StreamEvent(event_type="token", execution_id=execution_id, data={"token": team_msg})
    
    # ========== FASE 2: CONSENSO ==========
    
    yield StreamEvent(
        event_type="node_start",
        execution_id=execution_id,
        node_id="consensus",
        node_name="Proceso de consenso",
        data={"max_rounds": coordinator.consensus_engine.max_rounds}
    )
    
    if emit_brain_events:
        response_parts.append(brain_event("consensus", phase="starting", rounds_max=3))
    
    result = await coordinator.consensus_engine.run(
        agents=selected_agents,
        task=task,
        context=context
    )
    
    yield StreamEvent(
        event_type="node_end",
        execution_id=execution_id,
        node_id="consensus",
        data={"rounds_taken": result.rounds_taken, "success": result.success}
    )
    
    if emit_brain_events:
        response_parts.append(brain_event(
            "consensus",
            phase="completed",
            rounds=result.rounds_taken,
            lead_agent=result.lead_agent
        ))
    
    # Mostrar resultado
    consensus_msg = f"\n**Consenso alcanzado** en {result.rounds_taken} rondas\n\n"
    consensus_msg += "**Contribuciones del equipo:**\n"
    for proposal in result.proposals:
        summary = coordinator._summarize_proposal(proposal.content)
        consensus_msg += f"- **{proposal.agent_name}**: {summary}\n"
    consensus_msg += "\n"
    
    response_parts.append(consensus_msg)
    yield StreamEvent(event_type="token", execution_id=execution_id, data={"token": consensus_msg})
    
    # ========== FASE 3: EJECUCIÓN ==========
    
    if result.lead_agent:
        yield StreamEvent(
            event_type="node_start",
            execution_id=execution_id,
            node_id="execution",
            node_name="Ejecución final",
            data={"lead_agent": result.lead_agent}
        )
        
        if emit_brain_events:
            response_parts.append(brain_event("execution", phase="starting", lead_agent=result.lead_agent))
        
        lead_agent = subagent_registry.get(result.lead_agent)
        if lead_agent:
            exec_msg = f"\n**Ejecutando con {lead_agent.name}...**\n\n"
            response_parts.append(exec_msg)
            yield StreamEvent(event_type="token", execution_id=execution_id, data={"token": exec_msg})
            
            # Preparar task con brief consensuado
            execution_task = json.dumps({
                "mode": "execute",
                "original_task": task,
                "consensus_brief": result.merged_brief,
                "contributions": {p.agent_id: p.content for p in result.proposals}
            })
            
            try:
                exec_result = await lead_agent.execute(
                    task=execution_task,
                    context=context,
                    **llm_config
                )
                
                if exec_result.success:
                    response_parts.append(exec_result.response)
                    yield StreamEvent(event_type="token", execution_id=execution_id, data={"token": exec_result.response})
                    
                    # Brain Events especiales (artifacts, imágenes)
                    if exec_result.images:
                        for img in exec_result.images:
                            if emit_brain_events:
                                response_parts.append(brain_event(
                                    "artifact",
                                    artifact_type="image",
                                    url=img.get("url", "")
                                ))
                else:
                    error_msg = f"\nError en ejecución: {exec_result.error}\n"
                    response_parts.append(error_msg)
                    yield StreamEvent(event_type="token", execution_id=execution_id, data={"token": error_msg})
                    
            except Exception as e:
                logger.error(f"Execution error: {e}", exc_info=True)
                error_msg = f"\nError: {str(e)}\n"
                response_parts.append(error_msg)
                yield StreamEvent(event_type="token", execution_id=execution_id, data={"token": error_msg})
        
        yield StreamEvent(
            event_type="node_end",
            execution_id=execution_id,
            node_id="execution",
            data={"completed": True}
        )
    
    # ========== FINALIZACIÓN ==========
    
    elapsed = time.time() - start_time
    
    if emit_brain_events:
        response_parts.append(brain_event("team", action="completed", elapsed_ms=int(elapsed * 1000)))
    
    final_msg = f"\n---\n*Proceso completado en {elapsed:.1f}s con {len(selected_agents)} agentes*\n"
    response_parts.append(final_msg)
    yield StreamEvent(event_type="token", execution_id=execution_id, data={"token": final_msg})
    
    # Respuesta completa
    full_response = "".join(response_parts)
    yield StreamEvent(
        event_type="end",
        execution_id=execution_id,
        data={
            "output": {
                "response": full_response,
                "team_size": len(selected_agents),
                "consensus_rounds": result.rounds_taken,
                "elapsed_ms": int(elapsed * 1000)
            }
        }
    )
    
    yield {"_result": {"response": full_response}}
