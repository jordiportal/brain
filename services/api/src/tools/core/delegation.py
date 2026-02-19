"""
Delegation Tool - Permite al Adaptive Agent delegar a subagentes especializados

Esta tool permite al agente principal (Adaptive Agent) delegar tareas
a subagentes especializados por dominio:
- designer_agent: Generación y manipulación de imágenes, vídeos y presentaciones
- researcher_agent: Búsqueda e investigación web
- communication_agent: Estrategia y comunicación
- sap_analyst: Análisis de datos SAP S/4HANA, ECC y BI

Soporta delegación secuencial (delegate) y paralela (parallel_delegate).
"""

import asyncio
import time
import uuid
from typing import Dict, Any, Optional, List, Literal

import structlog

logger = structlog.get_logger()


async def _get_subagent_llm_config(agent_id: str, parent_llm_url: Optional[str], 
                                   parent_model: Optional[str], parent_provider_type: Optional[str],
                                   parent_api_key: Optional[str]) -> Dict[str, Optional[str]]:
    """
    Obtiene la configuración LLM para un subagente.
    
    Prioridad:
    1. Configuración guardada en subagent_configs (si existe llm_provider_id)
    2. Configuración del agente padre (heredada)
    3. Error - no hay proveedor disponible
    
    Returns:
        Dict con llm_url, model, provider_type, api_key
    """
    try:
        from src.db.repositories.subagent_configs import SubagentConfigRepository
        from src.db.repositories.llm_providers import LLMProviderRepository
        
        # 1. Buscar config específica del subagente
        subagent_config = await SubagentConfigRepository.get_by_agent_id(agent_id)
        
        if subagent_config and subagent_config.llm_provider_id:
            # El subagente tiene un proveedor configurado
            provider = await LLMProviderRepository.get_by_id(subagent_config.llm_provider_id)
            
            if provider and provider.is_active:
                logger.info(
                    f"Using subagent-specific LLM config",
                    agent_id=agent_id,
                    provider_id=provider.id,
                    provider_name=provider.name,
                    provider_type=provider.type
                )
                return {
                    "llm_url": provider.base_url,
                    "model": subagent_config.llm_model or provider.default_model,
                    "provider_type": provider.type,
                    "api_key": provider.api_key
                }
            elif provider:
                logger.warning(
                    f"Subagent LLM provider is inactive",
                    agent_id=agent_id,
                    provider_id=provider.id,
                    provider_name=provider.name
                )
        
        # 2. Si no hay config específica, usar la del padre (si existe y tiene provider_type)
        if parent_llm_url and parent_provider_type:
            logger.info(
                f"Using parent LLM config for subagent",
                agent_id=agent_id,
                parent_url=parent_llm_url,
                parent_provider=parent_provider_type
            )
            return {
                "llm_url": parent_llm_url,
                "model": parent_model,
                "provider_type": parent_provider_type,
                "api_key": parent_api_key
            }
        
        # 3. No hay configuración disponible
        logger.error(
            f"No LLM configuration available for subagent",
            agent_id=agent_id,
            has_parent_config=bool(parent_llm_url),
            has_subagent_config=bool(subagent_config and subagent_config.llm_provider_id)
        )
        
        raise ValueError(
            f"No hay configuración LLM disponible para el subagente '{agent_id}'. "
            f"Configure un proveedor LLM para este subagente en la sección de Configuración."
        )
        
    except Exception as e:
        logger.error(f"Error resolving subagent LLM config: {e}", agent_id=agent_id)
        # Si hay error en la BD, intentar usar la del padre como fallback
        if parent_llm_url:
            return {
                "llm_url": parent_llm_url,
                "model": parent_model,
                "provider_type": parent_provider_type,
                "api_key": parent_api_key
            }
        raise


async def delegate(
    agent: str,
    task: str,
    context: Optional[str] = None,
    # Contexto LLM heredado del Adaptive Agent
    _llm_url: Optional[str] = None,
    _model: Optional[str] = None,
    _provider_type: Optional[str] = None,
    _api_key: Optional[str] = None,
    _session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Delega una tarea a un subagente especializado.
    
    El Adaptive Agent usa esta tool cuando detecta que una tarea
    requiere capacidades especializadas de un dominio específico.
    
    Args:
        agent: ID del subagente (media_agent, sap_agent, mail_agent, office_agent)
        task: Descripción clara de la tarea a realizar
        context: Contexto adicional o resultados de pasos previos
        _llm_url: URL del LLM (inyectada por el sistema)
        _model: Modelo LLM (inyectado por el sistema)
        _provider_type: Tipo de proveedor (inyectado por el sistema)
        _api_key: API key (inyectada por el sistema)
    
    Returns:
        Dict con:
        - success: bool
        - response: Respuesta del subagente
        - agent_name: Nombre del subagente
        - tools_used: Lista de tools usadas
        - images: Lista de imágenes generadas (si aplica)
        - sources: Lista de fuentes (si aplica)
        - error: Mensaje de error (si falló)
    
    Examples:
        # Generar una imagen
        result = await delegate(
            agent="media_agent",
            task="Genera una imagen de un atardecer en la playa"
        )
        
        # Consultar SAP (futuro)
        result = await delegate(
            agent="sap_agent",
            task="Obtener pedidos del día de hoy"
        )
    """
    start_time = time.time()
    
    logger.info(
        "🎯 Delegating to subagent",
        agent=agent,
        task=task[:100],
        has_context=bool(context)
    )
    
    # Importar aquí para evitar circular imports
    from src.engine.chains.agents import subagent_registry, register_all_subagents
    
    # Asegurar que los subagentes estén registrados
    if not subagent_registry.is_initialized():
        await register_all_subagents()
    
    # Obtener el subagente
    subagent = subagent_registry.get(agent)
    
    if not subagent:
        available = subagent_registry.list_ids()
        return {
            "success": False,
            "error": f"Subagente '{agent}' no encontrado",
            "available_agents": available,
            "agent": agent
        }
    
    try:
        # Obtener configuración LLM del subagente (o heredar del padre)
        llm_config = await _get_subagent_llm_config(
            agent, _llm_url, _model, _provider_type, _api_key
        )
        
        # Mismo bucle que el agente principal (run_session_loop), no subagente.execute()
        from src.engine.chains.adaptive.executor import (
            run_session_loop,
            AgentContext,
            SessionLoopResult,
        )
        from src.engine.chains.agents.base import SubAgentResult
        
        child_session_id = f"{_session_id or 'root'}-{agent}-{uuid.uuid4().hex[:8]}"
        agent_context = AgentContext(
            session_id=child_session_id,
            parent_id=_session_id,
            agent_type=agent,
            max_iterations=12,
        )
        
        # Mensajes iniciales: system del subagente + memoria opcional + user (task + context)
        system_content = subagent.system_prompt + (subagent.get_skills_for_prompt() or "")
        messages = [{"role": "system", "content": system_content}]
        if _session_id:
            memory = subagent._load_memory(_session_id, max_messages=getattr(subagent, "MAX_MEMORY_MESSAGES", 10))
            for msg in memory:
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        user_content = f"Tarea: {task}"
        if context:
            user_content += f"\n\nContexto adicional: {context}"
        messages.append({"role": "user", "content": user_content})
        
        # Tools del subagente en formato LLM (sin delegate)
        subagent_tools = subagent.get_tools()
        tools_llm = [t.to_function_schema() for t in subagent_tools]
        
        loop_result: SessionLoopResult = await run_session_loop(
            execution_id=child_session_id,
            messages=messages,
            tools=tools_llm,
            llm_url=llm_config["llm_url"],
            model=llm_config["model"],
            provider_type=llm_config["provider_type"],
            api_key=llm_config["api_key"],
            agent_context=agent_context,
            emit_brain_events=False,
        )
        
        tools_used = [tr["tool"] for tr in loop_result.tool_results]
        response_text = loop_result.final_answer or ""
        if not response_text and loop_result.tool_results:
            response_text = f"Ejecutado en {loop_result.iteration} iteraciones. Herramientas: {', '.join(tools_used)}"
        
        # Guardar memoria de la sesión (subagente) si hay session_id
        if _session_id and response_text:
            subagent._save_memory(
                _session_id,
                user_content,
                response_text,
                max_messages=getattr(subagent, "MAX_MEMORY_MESSAGES", 10),
            )
        
        result = SubAgentResult(
            success=True,
            response=response_text,
            agent_id=subagent.id,
            agent_name=subagent.name,
            tools_used=tools_used,
            images=loop_result.images,
            videos=loop_result.videos,
            data={"tool_results": loop_result.tool_results} if loop_result.tool_results else {},
            execution_time_ms=int((time.time() - start_time) * 1000),
        )
        logger.info(
            "✅ Delegation completed (shared loop)",
            agent=agent,
            success=result.success,
            tools_used=result.tools_used,
            has_images=len(result.images) > 0,
            execution_time_ms=result.execution_time_ms,
        )
        return result.to_dict()
        
    except Exception as e:
        logger.error(f"❌ Delegation error: {e}", agent=agent, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "agent": agent,
            "execution_time_ms": int((time.time() - start_time) * 1000)
        }


async def get_available_subagents_description() -> str:
    """
    Genera descripción de subagentes disponibles para inyectar en prompts.
    
    Returns:
        String con descripción de cada subagente y sus capacidades
    """
    from src.engine.chains.agents import subagent_registry, register_all_subagents
    
    if not subagent_registry.is_initialized():
        await register_all_subagents()
    
    return subagent_registry.get_description()


async def get_subagent_ids() -> list:
    """
    Obtiene lista de IDs de subagentes disponibles.
    
    Returns:
        Lista de IDs (para enum en schema de tool)
    """
    from src.engine.chains.agents import subagent_registry, register_all_subagents
    
    if not subagent_registry.is_initialized():
        await register_all_subagents()
    
    return subagent_registry.list_ids()


async def consult_team_member(
    agent: str,
    task: str,
    context: Optional[str] = None,
    _llm_url: Optional[str] = None,
    _model: Optional[str] = None,
    _provider_type: Optional[str] = None,
    _api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Consulta a un miembro del equipo para obtener su opinión o propuesta (sin ejecutar la tarea completa).
    
    Usa esta tool en modo Team para que cada subagente aporte su perspectiva; luego usa think/reflect/plan
    para sintetizar y alcanzar consenso. No ejecuta la tarea final del subagente, solo su "propuesta".
    
    Args:
        agent: ID del subagente (media_agent, slides_agent, analyst_agent, communication_agent)
        task: Pregunta o tema sobre el que quieres la opinión del experto
        context: Contexto adicional (ej. propuestas de otros miembros)
        _llm_url, _model, _provider_type, _api_key: Config LLM (inyectada por el sistema)
    
    Returns:
        Dict con response (texto de la propuesta/opinión), agent_name, success.
    """
    from src.engine.chains.agents import subagent_registry, register_all_subagents
    
    if not subagent_registry.is_initialized():
        await register_all_subagents()
    
    subagent = subagent_registry.get(agent)
    if not subagent:
        available = subagent_registry.list_ids()
        return {
            "success": False,
            "error": f"Subagente '{agent}' no encontrado",
            "available_agents": available,
            "agent": agent
        }
    
    try:
        # Obtener configuración LLM del subagente (o heredar del padre)
        llm_config = await _get_subagent_llm_config(
            agent, _llm_url, _model, _provider_type, _api_key
        )
        
        result = await subagent.consult(
            topic=task,
            context=context,
            llm_url=llm_config["llm_url"],
            model=llm_config["model"],
            provider_type=llm_config["provider_type"],
            api_key=llm_config["api_key"]
        )
        return {
            "success": result.success,
            "response": result.response,
            "agent_id": result.agent_id,
            "agent_name": result.agent_name,
            "data": result.data,
            "error": result.error
        }
    except Exception as e:
        logger.error(f"Consult team member error: {e}", agent=agent, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "agent": agent,
            "agent_name": getattr(subagent, "name", agent)
        }


async def _execute_child_task(
    subagent,
    task: str,
    context: Optional[str],
    llm_config: Dict[str, Optional[str]],
    parent_execution_id: str
) -> Dict[str, Any]:
    """
    Ejecuta una tarea de subagente como ejecución hija.
    
    Cada ejecución hija tiene su propio execution_id vinculado al padre
    para trazabilidad completa del árbol de ejecución.
    
    Args:
        subagent: Instancia del subagente
        task: Tarea a ejecutar
        context: Contexto opcional
        llm_config: Configuración LLM resuelta
        parent_execution_id: ID de la ejecución padre
    
    Returns:
        Dict con resultado + metadatos de ejecución hija
    """
    child_execution_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(
        "🔀 Child execution started",
        child_id=child_execution_id[:8],
        parent_id=parent_execution_id[:8],
        agent=subagent.id,
        task=task[:80]
    )
    
    try:
        result = await subagent.execute(
            task=task,
            context=context,
            session_id=None,
            llm_url=llm_config["llm_url"],
            model=llm_config["model"],
            provider_type=llm_config["provider_type"],
            api_key=llm_config["api_key"]
        )
        
        execution_time = int((time.time() - start_time) * 1000)
        
        logger.info(
            "✅ Child execution completed",
            child_id=child_execution_id[:8],
            agent=subagent.id,
            success=result.success,
            execution_time_ms=execution_time
        )
        
        result_dict = result.to_dict()
        result_dict["_child_execution_id"] = child_execution_id
        result_dict["_parent_execution_id"] = parent_execution_id
        result_dict["execution_time_ms"] = execution_time
        return result_dict
        
    except Exception as e:
        execution_time = int((time.time() - start_time) * 1000)
        logger.error(
            f"❌ Child execution failed: {e}",
            child_id=child_execution_id[:8],
            agent=subagent.id,
            exc_info=True
        )
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "agent_id": subagent.id,
            "agent_name": subagent.name,
            "_child_execution_id": child_execution_id,
            "_parent_execution_id": parent_execution_id,
            "execution_time_ms": execution_time
        }


async def parallel_delegate(
    tasks: List[Dict[str, Any]],
    _llm_url: Optional[str] = None,
    _model: Optional[str] = None,
    _provider_type: Optional[str] = None,
    _api_key: Optional[str] = None,
    _execution_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Delega múltiples tareas a subagentes en paralelo.
    
    Lanza ejecuciones hijas concurrentes, cada una con su propio
    execution_id vinculado al padre. Ideal para tareas independientes
    que pueden ejecutarse simultáneamente.
    
    Args:
        tasks: Lista de tareas. Cada una es un dict con:
            - agent: ID del subagente (obligatorio)
            - task: Descripción de la tarea (obligatorio)
            - context: Contexto adicional (opcional)
        _llm_url: URL del LLM (inyectada por el sistema)
        _model: Modelo LLM (inyectado por el sistema)
        _provider_type: Tipo de proveedor (inyectado por el sistema)
        _api_key: API key (inyectada por el sistema)
        _execution_id: ID de la ejecución padre (inyectado por el sistema)
    
    Returns:
        Dict con:
        - success: bool (True si al menos uno tuvo éxito)
        - results: Lista de resultados por subagente
        - summary: Resumen de ejecución
        - child_execution_ids: IDs de ejecuciones hijas
        - total_execution_time_ms: Tiempo total (wall clock)
    
    Examples:
        result = await parallel_delegate(tasks=[
            {"agent": "researcher_agent", "task": "Investiga tendencias IA 2025"},
            {"agent": "designer_agent", "task": "Genera imagen de robot futurista"}
        ])
    """
    start_time = time.time()
    parent_id = _execution_id or str(uuid.uuid4())
    
    logger.info(
        "🔀 Parallel delegation started",
        parent_id=parent_id[:8],
        num_tasks=len(tasks),
        agents=[t.get("agent") for t in tasks]
    )
    
    # Validar tareas
    if not tasks or not isinstance(tasks, list):
        return {
            "success": False,
            "error": "Se requiere una lista de tareas con al menos un elemento",
            "results": []
        }
    
    if len(tasks) > 5:
        return {
            "success": False,
            "error": "Máximo 5 tareas en paralelo para evitar sobrecarga",
            "results": []
        }
    
    # Importar aquí para evitar circular imports
    from src.engine.chains.agents import subagent_registry, register_all_subagents
    
    if not subagent_registry.is_initialized():
        await register_all_subagents()
    
    # Validar que todos los agentes existen antes de lanzar
    validated_tasks = []
    errors = []
    
    for i, task_def in enumerate(tasks):
        agent_id = task_def.get("agent")
        task_text = task_def.get("task")
        context = task_def.get("context")
        
        if not agent_id or not task_text:
            errors.append({
                "index": i,
                "error": "Cada tarea necesita 'agent' y 'task'",
                "task_def": task_def
            })
            continue
        
        subagent = subagent_registry.get(agent_id)
        if not subagent:
            available = subagent_registry.list_ids()
            errors.append({
                "index": i,
                "error": f"Subagente '{agent_id}' no encontrado",
                "available_agents": available
            })
            continue
        
        validated_tasks.append({
            "subagent": subagent,
            "task": task_text,
            "context": context,
            "agent_id": agent_id
        })
    
    if not validated_tasks:
        return {
            "success": False,
            "error": "Ninguna tarea válida para ejecutar",
            "validation_errors": errors,
            "results": []
        }
    
    # Resolver configuración LLM para cada subagente y crear coroutines
    coroutines = []
    for vt in validated_tasks:
        try:
            llm_config = await _get_subagent_llm_config(
                vt["agent_id"], _llm_url, _model, _provider_type, _api_key
            )
            coroutines.append(
                _execute_child_task(
                    subagent=vt["subagent"],
                    task=vt["task"],
                    context=vt["context"],
                    llm_config=llm_config,
                    parent_execution_id=parent_id
                )
            )
        except Exception as e:
            logger.error(f"Error resolving LLM config for {vt['agent_id']}: {e}")
            errors.append({
                "agent_id": vt["agent_id"],
                "error": f"Error configuración LLM: {str(e)}"
            })
    
    if not coroutines:
        return {
            "success": False,
            "error": "No se pudo preparar ninguna ejecución",
            "validation_errors": errors,
            "results": []
        }
    
    # Ejecutar todas las tareas en paralelo
    results = await asyncio.gather(*coroutines, return_exceptions=True)
    
    total_time = int((time.time() - start_time) * 1000)
    
    # Procesar resultados
    processed_results = []
    child_ids = []
    successes = 0
    failures = 0
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append({
                "success": False,
                "agent_id": validated_tasks[i]["agent_id"],
                "error": str(result),
                "error_type": type(result).__name__
            })
            failures += 1
        else:
            processed_results.append(result)
            child_id = result.get("_child_execution_id")
            if child_id:
                child_ids.append(child_id)
            if result.get("success"):
                successes += 1
            else:
                failures += 1
    
    # Agregar errores de validación como resultados fallidos
    for err in errors:
        processed_results.append({
            "success": False,
            **err
        })
        failures += 1
    
    logger.info(
        "🔀 Parallel delegation completed",
        parent_id=parent_id[:8],
        successes=successes,
        failures=failures,
        total_time_ms=total_time,
        child_ids=[cid[:8] for cid in child_ids]
    )
    
    return {
        "success": successes > 0,
        "results": processed_results,
        "child_execution_ids": child_ids,
        "summary": {
            "total_tasks": len(tasks),
            "successes": successes,
            "failures": failures,
            "total_execution_time_ms": total_time,
            "agents_used": [vt["agent_id"] for vt in validated_tasks]
        }
    }


async def get_agent_info(agent: str) -> Dict[str, Any]:
    """
    Obtiene información sobre un subagente, incluyendo su rol, expertise y qué datos necesita.
    
    Usa esta tool ANTES de delegar para:
    1. Conocer el rol profesional del subagente
    2. Saber en qué puede ayudarte (expertise)
    3. Entender qué formato de datos necesita
    
    Args:
        agent: ID del subagente (media_agent, slides_agent, etc.)
    
    Returns:
        Dict con información completa del subagente
    """
    from src.engine.chains.agents import subagent_registry, register_all_subagents
    
    if not subagent_registry.is_initialized():
        await register_all_subagents()
    
    subagent = subagent_registry.get(agent)
    
    if not subagent:
        available = subagent_registry.list_ids()
        return {
            "success": False,
            "error": f"Subagente '{agent}' no encontrado",
            "available_agents": available
        }
    
    return {
        "success": True,
        "id": subagent.id,
        "name": subagent.name,
        "role": getattr(subagent, 'role', 'Especialista'),
        "expertise": getattr(subagent, 'expertise', subagent.description),
        "task_requirements": subagent.task_requirements,
        "supports_consult_mode": True,  # Todos los subagentes ahora soportan consulta
        "version": subagent.version
    }


# ============================================
# Tool Definitions
# ============================================

def _get_agent_ids() -> list:
    """Obtiene IDs de subagentes registrados (enum dinámico).
    Sync helper - relies on registry being initialized at startup."""
    try:
        from src.engine.chains.agents import subagent_registry
        if subagent_registry.is_initialized():
            return subagent_registry.list_ids()
        return ["designer_agent", "researcher_agent", "communication_agent"]
    except Exception:
        return ["designer_agent", "researcher_agent", "communication_agent"]


def get_agent_info_tool() -> dict:
    """Tool get_agent_info con enum dinámico."""
    return {
        "id": "get_agent_info",
        "name": "get_agent_info",
        "description": """Obtiene información sobre un subagente (rol, expertise, formato de datos).

Usa ANTES de delegar para saber qué espera cada subagente.""",
        "parameters": {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "enum": _get_agent_ids(),
                    "description": "ID del subagente"
                }
            },
            "required": ["agent"]
        },
        "handler": get_agent_info
    }


def get_delegate_tool() -> dict:
    """Tool delegate con enum dinámico."""
    from src.engine.chains.agents.base import subagent_registry

    agent_lines = []
    for a in subagent_registry.list():
        agent_lines.append(f"- {a.id}: {a.description}")
    agents_desc = "\n".join(agent_lines) if agent_lines else "No hay subagentes configurados."

    return {
        "id": "delegate",
        "name": "delegate",
        "description": f"Delega una tarea a un subagente. Usa get_agent_info primero si no conoces el formato.\n\n{agents_desc}",
        "parameters": {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "enum": _get_agent_ids(),
                    "description": "ID del subagente"
                },
                "task": {
                    "type": "string",
                    "description": "Tarea para el subagente"
                },
                "context": {
                    "type": "string",
                    "description": "Contexto adicional (opcional)"
                }
            },
            "required": ["agent", "task"]
        },
        "handler": delegate
    }


def get_consult_team_member_tool() -> dict:
    """Tool consult_team_member con enum dinámico."""
    return {
        "id": "consult_team_member",
        "name": "consult_team_member",
        "description": """Consulta a un miembro del equipo (obtiene opinión, no ejecuta).

Usa think/reflect/plan para sintetizar las propuestas.""",
        "parameters": {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "enum": _get_agent_ids(),
                    "description": "ID del miembro"
                },
                "task": {
                    "type": "string",
                    "description": "Pregunta o tema"
                },
                "context": {
                    "type": "string",
                    "description": "Contexto adicional"
                }
            },
            "required": ["agent", "task"]
        },
        "handler": consult_team_member
    }


def get_parallel_delegate_tool() -> dict:
    """Tool parallel_delegate con enum dinámico."""
    return {
        "id": "parallel_delegate",
        "name": "parallel_delegate",
        "description": """Delega múltiples tareas a subagentes en PARALELO (ejecución concurrente).

Usa cuando necesites ejecutar tareas INDEPENDIENTES simultáneamente para ahorrar tiempo.
Cada subagente se ejecuta como ejecución hija con su propio contexto aislado.

Ejemplos de uso:
- Investigar un tema CON researcher_agent Y generar imagen CON designer_agent al mismo tiempo
- Consultar datos SAP Y buscar en web simultáneamente

NO usar cuando una tarea dependa del resultado de otra (usar delegate secuencial).""",
        "parameters": {
            "type": "object",
            "properties": {
                "tasks": {
                    "type": "array",
                    "description": "Lista de tareas a ejecutar en paralelo (máximo 5)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "agent": {
                                "type": "string",
                                "enum": _get_agent_ids(),
                                "description": "ID del subagente"
                            },
                            "task": {
                                "type": "string",
                                "description": "Tarea para el subagente"
                            },
                            "context": {
                                "type": "string",
                                "description": "Contexto adicional (opcional)"
                            }
                        },
                        "required": ["agent", "task"]
                    },
                    "minItems": 1,
                    "maxItems": 5
                }
            },
            "required": ["tasks"]
        },
        "handler": parallel_delegate
    }


