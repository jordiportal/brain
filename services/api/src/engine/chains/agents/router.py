"""
Router para gestión de Subagentes Especializados

Endpoints para listar, configurar y probar subagentes.
La configuración de cada subagente (incluyendo LLM provider/modelo) se persiste
en la tabla subagent_configs de PostgreSQL.
"""

import json
import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import structlog

from src.db import get_db

from . import subagent_registry, register_all_subagents

logger = structlog.get_logger()

router = APIRouter(prefix="/subagents", tags=["Subagents"])


class SubagentExecuteRequest(BaseModel):
    """Request para ejecutar una tarea en un subagente"""
    task: str
    context: Optional[str] = None
    session_id: Optional[str] = None
    llm_url: Optional[str] = None
    model: Optional[str] = None
    provider_type: str = "ollama"
    api_key: Optional[str] = None


class SubagentConfigUpdate(BaseModel):
    """Request para actualizar configuración de un subagente"""
    enabled: bool = True
    system_prompt: Optional[str] = None
    # LLM para razonamiento del agente - referencia al ID del provider en BD
    llm_provider: Optional[int] = None  # ID del provider en llm_providers
    llm_model: Optional[str] = None  # Override del modelo (vacío = usar default del provider)
    settings: Dict[str, Any] = {}


# ============================================
# Listar y Obtener Subagentes
# ============================================

@router.get("")
async def list_subagents():
    """Lista todos los subagentes registrados"""
    # Asegurar que los subagentes estén registrados
    if not subagent_registry.is_initialized():
        await register_all_subagents()
    
    agents = subagent_registry.list()
    
    return {
        "subagents": [
            {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "version": agent.version,
                "domain_tools": agent.domain_tools,
                "skills": agent.list_available_skills(),
                "status": "active",  # TODO: Cargar desde config
                "icon": _get_agent_icon(agent.id)
            }
            for agent in agents
        ],
        "total": len(agents)
    }


# ── Examiner config (before {agent_id} routes to avoid path conflict) ──

_EXAMINER_CONFIG_KEY = "test_examiner_config"


class ExaminerConfigUpdate(BaseModel):
    provider_id: Optional[int] = None
    model: Optional[str] = None


@router.get("/config/test-examiner")
async def get_examiner_config():
    """Get the global examiner LLM configuration."""
    from src.db.repositories import BrainSettingsRepository
    val = await BrainSettingsRepository.get(_EXAMINER_CONFIG_KEY, {})
    return val or {}


@router.put("/config/test-examiner")
async def set_examiner_config(cfg: ExaminerConfigUpdate):
    """Save the global examiner LLM configuration."""
    from src.db.repositories import BrainSettingsRepository
    data = {"provider_id": cfg.provider_id, "model": cfg.model}
    try:
        await BrainSettingsRepository.upsert(_EXAMINER_CONFIG_KEY, data)
    except KeyError:
        db = get_db()
        await db.execute(
            """
            INSERT INTO brain_settings (key, value, type, category, label, description, is_public)
            VALUES ($1, $2::jsonb, 'json', 'tests', 'Examiner LLM Config', 'LLM config for auto-evaluating tests', false)
            """,
            _EXAMINER_CONFIG_KEY, json.dumps(data),
        )
    return data


# ============================================

@router.get("/{agent_id}")
async def get_subagent(agent_id: str):
    """Obtiene detalles de un subagente específico"""
    if not subagent_registry.is_initialized():
        await register_all_subagents()
    
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Subagente no encontrado: {agent_id}"
        )
    
    # Obtener herramientas del agente
    print(f"DEBUG: Getting tools for {agent_id}")
    tools = agent.get_tools()
    print(f"DEBUG: Got {len(tools)} tools for {agent_id}: {[t.id for t in tools]}")
    
    return {
        "subagent": {
            "id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "version": agent.version,
            "domain_tools": agent.domain_tools,
            "system_prompt": agent.system_prompt[:500] + "..." if len(agent.system_prompt) > 500 else agent.system_prompt,
            "status": "active",
            "icon": _get_agent_icon(agent.id),
            "tools": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters
                }
                for t in tools
            ]
        }
    }


@router.get("/{agent_id}/tools")
async def get_subagent_tools(agent_id: str):
    """Obtiene las herramientas de un subagente"""
    if not subagent_registry.is_initialized():
        await register_all_subagents()
    
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Subagente no encontrado: {agent_id}"
        )
    
    tools = agent.get_tools()
    
    return {
        "agent_id": agent_id,
        "tools": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "type": t.type.value if hasattr(t.type, 'value') else str(t.type),
                "parameters": t.parameters
            }
            for t in tools
        ],
        "total": len(tools)
    }


# ============================================
# Ejecutar y Probar Subagentes
# ============================================

@router.post("/{agent_id}/execute")
async def execute_subagent(agent_id: str, request: SubagentExecuteRequest):
    """
    Ejecuta una tarea en un subagente específico.
    
    Prioridad de configuración LLM:
    1. Valores explícitos en la request
    2. Configuración guardada del subagente
    3. Provider por defecto del sistema
    """
    if not subagent_registry.is_initialized():
        await register_all_subagents()
    
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Subagente no encontrado: {agent_id}"
        )
    
    # Obtener configuración guardada del subagente desde BD
    config = await _get_agent_config(agent_id)
    
    # Resolver LLM: prioridad request > config guardada > default
    llm_url = request.llm_url
    model = request.model
    provider_type = request.provider_type
    api_key = request.api_key
    
    # Si no hay valores en request, usar configuración guardada
    if not llm_url and config.get("llm_provider"):
        provider_info = await _resolve_llm_provider(config["llm_provider"])
        if provider_info:
            llm_url = provider_info.get("base_url")
            model = config.get("llm_model") or provider_info.get("default_model")
            provider_type = provider_info.get("type", "ollama")
            api_key = provider_info.get("api_key")
            logger.info(
                f"🔧 Using saved config for {agent_id}",
                provider_id=config["llm_provider"],
                model=model
            )
    
    logger.info(
        f"🎯 Direct execution of subagent",
        agent_id=agent_id,
        task=request.task[:100],
        llm_url=llm_url,
        model=model
    )
    
    try:
        result = await agent.execute(
            task=request.task,
            context=request.context,
            session_id=request.session_id,
            llm_url=llm_url,
            model=model,
            provider_type=provider_type,
            api_key=api_key
        )
        
        return {
            "status": "completed",
            "agent_id": agent_id,
            "result": result.to_dict()
        }
        
    except Exception as e:
        logger.error(f"Error executing subagent {agent_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error ejecutando subagente: {str(e)}"
        )


@router.post("/{agent_id}/execute/stream")
async def execute_subagent_stream(agent_id: str, request: SubagentExecuteRequest):
    """
    Ejecuta un subagente con streaming SSE de eventos.
    Emite node_start, token, node_end, image, video, response_complete.
    """
    if not subagent_registry.is_initialized():
        await register_all_subagents()

    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Subagente no encontrado: {agent_id}")

    config = await _get_agent_config(agent_id)

    llm_url = request.llm_url
    model = request.model
    provider_type = request.provider_type
    api_key = request.api_key

    if not llm_url and config.get("llm_provider"):
        provider_info = await _resolve_llm_provider(config["llm_provider"])
        if provider_info:
            llm_url = provider_info.get("base_url")
            model = config.get("llm_model") or provider_info.get("default_model")
            provider_type = provider_info.get("type", "ollama")
            api_key = provider_info.get("api_key")

    if not llm_url or not model:
        raise HTTPException(status_code=400, detail="No LLM configured for this agent")

    session_id = request.session_id
    exec_id = session_id or str(uuid.uuid4())

    async def event_generator():
        from src.engine.chains.adaptive.executor import (
            run_session_loop_stream,
            AgentContext,
        )

        now = datetime.now()
        date_ctx = (
            f"\n\n## FECHA ACTUAL\n"
            f"Hoy es {now.strftime('%A %d de %B de %Y')} ({now.strftime('%Y-%m-%d')}). "
            f"Mes: {now.strftime('%Y%m')}. Ano: {now.year}.\n"
        )
        messages = [
            {"role": "system", "content": agent.system_prompt + date_ctx + agent.get_skills_for_prompt()}
        ]

        if session_id:
            for msg in agent._load_memory(session_id, max_messages=agent.MAX_MEMORY_MESSAGES):
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

        user_content = f"Tarea: {request.task}"
        if request.context:
            user_content += f"\n\nContexto adicional: {request.context}"
        messages.append({"role": "user", "content": user_content})

        tools_llm = [t.to_function_schema() for t in agent.get_tools()]

        agent_context = AgentContext(
            session_id=session_id,
            parent_id=None,
            agent_type=agent.id,
            max_iterations=12,
        )

        final_content = ""
        try:
            async for event in run_session_loop_stream(
                execution_id=exec_id,
                messages=messages,
                tools=tools_llm,
                llm_url=llm_url,
                model=model,
                provider_type=provider_type,
                api_key=api_key,
                agent_context=agent_context,
                emit_brain_events=False,
            ):
                event_data = {
                    "event_type": event.event_type,
                    "execution_id": event.execution_id,
                    "timestamp": event.timestamp.isoformat(),
                    "node_id": event.node_id,
                    "node_name": event.node_name,
                    "content": event.content,
                    "data": event.data,
                }
                yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

                if event.event_type == "response_complete" and event.content:
                    final_content = event.content

            if session_id and final_content:
                agent._save_memory(
                    session_id, user_content, final_content,
                    max_messages=agent.MAX_MEMORY_MESSAGES,
                )

        except Exception as e:
            logger.error(f"Stream error for {agent_id}: {e}", exc_info=True)
            error_event = {
                "event_type": "error",
                "execution_id": exec_id,
                "data": {"error": str(e)},
            }
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{agent_id}/test")
async def test_subagent(agent_id: str):
    """
    Prueba rápida de un subagente.
    
    Verifica que el subagente está correctamente configurado y sus tools funcionan.
    """
    if not subagent_registry.is_initialized():
        await register_all_subagents()
    
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Subagente no encontrado: {agent_id}"
        )
    
    # Verificar tools
    tools = agent.get_tools()
    tools_status = []
    
    for tool in tools:
        tools_status.append({
            "id": tool.id,
            "name": tool.name,
            "has_handler": tool.handler is not None,
            "status": "ok" if tool.handler else "missing_handler"
        })
    
    all_ok = all(t["status"] == "ok" for t in tools_status)
    
    return {
        "agent_id": agent_id,
        "status": "healthy" if all_ok else "degraded",
        "tools_count": len(tools),
        "tools_status": tools_status,
        "checks": {
            "registered": True,
            "has_tools": len(tools) > 0,
            "all_handlers_present": all_ok
        }
    }


# ============================================
# Configuración de Subagentes
# ============================================

@router.get("/{agent_id}/config")
async def get_subagent_config(agent_id: str):
    """Obtiene la configuración actual de un subagente desde PostgreSQL"""
    if not subagent_registry.is_initialized():
        await register_all_subagents()
    
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Subagente no encontrado: {agent_id}"
        )
    
    # Cargar configuración desde BD
    config = await _get_agent_config(agent_id)
    
    # Añadir system_prompt del agente (si no hay override en BD)
    if not config.get("system_prompt"):
        config["system_prompt"] = agent.system_prompt
    
    return {
        "agent_id": agent_id,
        "config": config
    }


@router.put("/{agent_id}/config")
async def update_subagent_config(agent_id: str, config: SubagentConfigUpdate):
    """Actualiza la configuración de un subagente en PostgreSQL (incluyendo LLM provider/modelo)"""
    from src.db.repositories import SubagentConfigRepository
    
    if not subagent_registry.is_initialized():
        await register_all_subagents()
    
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Subagente no encontrado: {agent_id}"
        )
    
    # Actualizar system_prompt en memoria del agente si se proporciona
    if config.system_prompt is not None:
        agent.system_prompt = config.system_prompt
        logger.info(
            f"📝 Updated system_prompt for {agent_id}",
            prompt_length=len(config.system_prompt)
        )
    
    try:
        # Guardar configuración completa en PostgreSQL con UPSERT
        saved_config = await SubagentConfigRepository.upsert(
            agent_id=agent_id,
            is_enabled=config.enabled,
            llm_provider_id=config.llm_provider,
            llm_model=config.llm_model,
            system_prompt=config.system_prompt,
            settings=config.settings
        )
        
        logger.info(
            f"📝 Subagent config saved to PostgreSQL",
            agent_id=agent_id,
            enabled=config.enabled,
            llm_provider=config.llm_provider,
            llm_model=config.llm_model,
            config_id=saved_config.id
        )
        
        return {
            "status": "ok",
            "message": f"Configuración de {agent_id} guardada en BD",
            "agent_id": agent_id,
            "config_id": saved_config.id,
            "updated": {
                "system_prompt": config.system_prompt is not None,
                "enabled": config.enabled,
                "llm_provider": config.llm_provider,
                "llm_model": config.llm_model
            }
        }
    except Exception as e:
        logger.error(f"Error saving subagent config: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error guardando configuración: {str(e)}"
        )


# ============================================
# Skills de Subagentes
# ============================================

@router.get("/{agent_id}/skills")
async def get_subagent_skills(agent_id: str):
    """Obtiene los skills disponibles de un subagente"""
    if not subagent_registry.is_initialized():
        await register_all_subagents()
    
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Subagente no encontrado: {agent_id}"
        )
    
    skills = agent.list_available_skills()
    
    return {
        "agent_id": agent_id,
        "skills": skills,
        "total": len(skills)
    }


@router.get("/{agent_id}/skills/{skill_id}")
async def get_skill_content(agent_id: str, skill_id: str):
    """Obtiene el contenido de un skill específico"""
    if not subagent_registry.is_initialized():
        await register_all_subagents()
    
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Subagente no encontrado: {agent_id}"
        )
    
    # Verificar que el skill existe
    available_skills = [s["id"] for s in agent.list_available_skills()]
    if skill_id not in available_skills:
        raise HTTPException(
            status_code=404,
            detail=f"Skill no encontrado: {skill_id}"
        )
    
    # Cargar contenido del skill
    result = agent.load_skill(skill_id)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Error cargando skill")
        )
    
    return {
        "agent_id": agent_id,
        "skill_id": skill_id,
        "content": result.get("content", ""),
        "chars": len(result.get("content", ""))
    }


class SkillContentUpdate(BaseModel):
    """Request para actualizar contenido de un skill"""
    content: str


@router.put("/{agent_id}/skills/{skill_id}")
async def update_skill_content(agent_id: str, skill_id: str, update: SkillContentUpdate):
    """Actualiza el contenido de un skill"""
    if not subagent_registry.is_initialized():
        await register_all_subagents()
    
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Subagente no encontrado: {agent_id}"
        )
    
    # Verificar que el skill existe
    available_skills = [s["id"] for s in agent.list_available_skills()]
    if skill_id not in available_skills:
        raise HTTPException(
            status_code=404,
            detail=f"Skill no encontrado: {skill_id}"
        )
    
    # Guardar contenido en el archivo
    try:
        skills_dir = agent.get_skills_dir()
        skill_file = skills_dir / f"{skill_id}.md"
        
        if not skills_dir.exists():
            skills_dir.mkdir(parents=True, exist_ok=True)
        
        skill_file.write_text(update.content, encoding="utf-8")
        
        # Invalidar cache
        if skill_id in agent._skills_cache:
            del agent._skills_cache[skill_id]
        
        logger.info(
            f"📝 Updated skill content",
            agent_id=agent_id,
            skill_id=skill_id,
            chars=len(update.content)
        )
        
        return {
            "status": "ok",
            "message": f"Skill '{skill_id}' actualizado",
            "agent_id": agent_id,
            "skill_id": skill_id,
            "chars": len(update.content)
        }
        
    except Exception as e:
        logger.error(f"Error saving skill {skill_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error guardando skill: {str(e)}"
        )


# ============================================
# Tests de Subagentes
# ============================================

class TestResultUpdate(BaseModel):
    """Request para actualizar resultado de un test"""
    status: str  # pass, fail, pending
    notes: Optional[str] = None


class EvaluateRequest(BaseModel):
    llm_url: str
    model: str
    provider_type: str = "ollama"
    api_key: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None


@router.get("/{agent_id}/tests")
async def get_subagent_tests(agent_id: str):
    """Obtiene los tests definidos para un subagente"""
    if not subagent_registry.is_initialized():
        await register_all_subagents()
    
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Subagente no encontrado: {agent_id}"
        )
    
    # Cargar tests desde archivos JSON
    tests = _load_agent_tests(agent_id)
    
    # Cargar resultados guardados
    results = _load_test_results(agent_id)
    
    # Combinar tests con sus resultados
    for category in tests:
        for test in category.get("tests", []):
            test_id = test["id"]
            if test_id in results:
                test["lastRun"] = results[test_id]
    
    return {
        "agent_id": agent_id,
        "categories": tests,
        "total_tests": sum(len(c.get("tests", [])) for c in tests)
    }


@router.post("/{agent_id}/tests/{test_id}/run")
async def run_subagent_test(
    agent_id: str, 
    test_id: str,
    llm_url: Optional[str] = None,
    model: Optional[str] = None,
    provider_type: str = "ollama",
    api_key: Optional[str] = None
):
    """Ejecuta un test específico de un subagente"""
    import time
    
    if not subagent_registry.is_initialized():
        await register_all_subagents()
    
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Subagente no encontrado: {agent_id}"
        )
    
    # Buscar el test
    test = _find_test(agent_id, test_id)
    if not test:
        raise HTTPException(
            status_code=404,
            detail=f"Test no encontrado: {test_id}"
        )
    
    logger.info(
        f"🧪 Running test",
        agent_id=agent_id,
        test_id=test_id,
        test_name=test.get("name")
    )
    
    start_time = time.time()
    
    try:
        result = await agent.execute(
            task=test["input"]["task"],
            context=test["input"].get("context"),
            llm_url=llm_url,
            model=model,
            provider_type=provider_type,
            api_key=api_key
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        result_dict = result.to_dict()

        extracted = _extract_test_artifacts(result_dict)

        _persist_execution(agent_id, test_id, {
            "duration_ms": duration_ms,
            "tools_used": result_dict.get("tools_used", []),
            "has_html": extracted["html"] is not None,
            "has_images": result_dict.get("has_images", False),
            "success": result_dict.get("success", False),
            "response_preview": (result_dict.get("response") or "")[:200],
            "timestamp": datetime.now().isoformat(),
        })

        return {
            "agent_id": agent_id,
            "test_id": test_id,
            "test_name": test["name"],
            "status": "executed",
            "duration_ms": duration_ms,
            "result": result_dict,
            "html": extracted["html"],
            "artifact_urls": extracted["artifact_urls"],
            "expected": test["expected"],
            "criteria": test["expected"].get("criteria", [])
        }
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Test execution error: {e}", exc_info=True)

        _persist_execution(agent_id, test_id, {
            "duration_ms": duration_ms,
            "error": str(e),
            "success": False,
            "timestamp": datetime.now().isoformat(),
        })
        
        return {
            "agent_id": agent_id,
            "test_id": test_id,
            "test_name": test["name"],
            "status": "error",
            "duration_ms": duration_ms,
            "error": str(e),
            "expected": test["expected"],
            "criteria": test["expected"].get("criteria", [])
        }


@router.put("/{agent_id}/tests/{test_id}/result")
async def update_test_result(agent_id: str, test_id: str, update: TestResultUpdate):
    """Guarda el resultado de validación manual de un test"""
    if not subagent_registry.is_initialized():
        await register_all_subagents()
    
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Subagente no encontrado: {agent_id}"
        )
    
    # Verificar que el test existe
    test = _find_test(agent_id, test_id)
    if not test:
        raise HTTPException(
            status_code=404,
            detail=f"Test no encontrado: {test_id}"
        )
    
    # Guardar resultado
    result = {
        "status": update.status,
        "notes": update.notes,
        "timestamp": datetime.now().isoformat()
    }
    
    _save_test_result(agent_id, test_id, result)
    
    logger.info(
        f"📝 Test result saved",
        agent_id=agent_id,
        test_id=test_id,
        status=update.status
    )
    
    return {
        "status": "ok",
        "agent_id": agent_id,
        "test_id": test_id,
        "result": result
    }


@router.post("/{agent_id}/tests/{test_id}/evaluate")
async def evaluate_test(agent_id: str, test_id: str, req: EvaluateRequest):
    """Evaluate a test result against its criteria using an independent examiner LLM."""
    if not subagent_registry.is_initialized():
        await register_all_subagents()
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Subagente no encontrado: {agent_id}")

    test = _find_test(agent_id, test_id)
    if not test:
        raise HTTPException(status_code=404, detail=f"Test no encontrado: {test_id}")

    criteria = test["expected"].get("criteria", [])
    if not criteria:
        return {"overall": "skip", "criteria_results": [], "reason": "Sin criterios definidos"}

    result_data = req.result_data
    if not result_data:
        results = _load_test_results(agent_id)
        exec_info = results.get(test_id, {}).get("lastExecution")
        if not exec_info:
            raise HTTPException(status_code=400, detail="No hay resultado de ejecución. Ejecuta el test primero.")
        result_data = exec_info

    evaluation = await _run_examiner(
        llm_url=req.llm_url,
        model=req.model,
        provider_type=req.provider_type,
        api_key=req.api_key,
        test_input=test["input"],
        criteria=criteria,
        result_data=result_data,
    )

    results = _load_test_results(agent_id)
    entry = results.get(test_id, {})
    entry["evaluation"] = evaluation
    results[test_id] = entry
    _save_test_results(agent_id, results)

    return evaluation


@router.post("/{agent_id}/tests/evaluate-all")
async def evaluate_all_tests(agent_id: str, req: EvaluateRequest):
    """Batch-evaluate all tests that have execution results."""
    if not subagent_registry.is_initialized():
        await register_all_subagents()
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Subagente no encontrado: {agent_id}")

    all_tests = _load_agent_tests(agent_id)
    results = _load_test_results(agent_id)
    evaluations: Dict[str, Any] = {}

    for category in all_tests:
        for test in category.get("tests", []):
            tid = test["id"]
            exec_info = results.get(tid, {}).get("lastExecution")
            if not exec_info:
                continue
            criteria = test["expected"].get("criteria", [])
            if not criteria:
                continue
            try:
                ev = await _run_examiner(
                    llm_url=req.llm_url,
                    model=req.model,
                    provider_type=req.provider_type,
                    api_key=req.api_key,
                    test_input=test["input"],
                    criteria=criteria,
                    result_data=exec_info,
                )
                entry = results.get(tid, {})
                entry["evaluation"] = ev
                results[tid] = entry
                evaluations[tid] = ev
            except Exception as e:
                logger.error(f"Evaluation error for {tid}: {e}")
                evaluations[tid] = {"overall": "error", "error": str(e)}

    _save_test_results(agent_id, results)
    return {"agent_id": agent_id, "evaluations": evaluations, "total": len(evaluations)}


def _load_agent_tests(agent_id: str) -> List[Dict[str, Any]]:
    """Carga los tests definidos para un subagente"""
    import json
    from pathlib import Path
    
    # Buscar directorio de tests del agente
    base_path = Path(__file__).parent / agent_id.replace("_agent", "") / "tests"
    
    if not base_path.exists():
        return []
    
    categories = []
    
    for test_file in sorted(base_path.glob("*.json")):
        # Ignorar archivos internos (empiezan con _)
        if test_file.stem.startswith("_"):
            continue
            
        try:
            with open(test_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                data["file"] = test_file.stem
                categories.append(data)
        except Exception as e:
            logger.error(f"Error loading test file {test_file}: {e}")
    
    return categories


def _find_test(agent_id: str, test_id: str) -> Optional[Dict[str, Any]]:
    """Busca un test específico por ID"""
    categories = _load_agent_tests(agent_id)
    
    for category in categories:
        for test in category.get("tests", []):
            if test["id"] == test_id:
                return test
    
    return None


def _load_test_results(agent_id: str) -> Dict[str, Any]:
    """Carga los resultados guardados de tests"""
    import json
    from pathlib import Path
    
    results_file = Path(__file__).parent / agent_id.replace("_agent", "") / "tests" / "_results.json"
    
    if not results_file.exists():
        return {}
    
    try:
        with open(results_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_test_result(agent_id: str, test_id: str, result: Dict[str, Any]) -> None:
    """Guarda el resultado manual de un test, preservando lastExecution."""
    results = _load_test_results(agent_id)
    entry = results.get(test_id, {})
    entry.update(result)
    results[test_id] = entry
    _save_test_results(agent_id, results)


async def _run_examiner(
    llm_url: str,
    model: str,
    provider_type: str,
    api_key: Optional[str],
    test_input: Dict[str, Any],
    criteria: List[str],
    result_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Call an LLM to evaluate test results against criteria."""
    from src.engine.chains.llm_utils import call_llm

    criteria_list = "\n".join(f"  {i+1}. {c}" for i, c in enumerate(criteria))
    system_prompt = (
        "You are a strict QA examiner. You evaluate test results against predefined criteria.\n"
        "For EACH criterion, respond with PASS or FAIL and a brief reason.\n"
        "At the end, give an overall verdict: PASS (all criteria met) or FAIL (any criterion failed).\n\n"
        "Respond ONLY with valid JSON in this format:\n"
        '{"criteria_results": [{"criterion": "...", "passed": true/false, "reason": "..."}], "overall": "pass" or "fail"}'
    )

    tools_used = result_data.get("tools_used", [])
    response_text = result_data.get("response_preview") or result_data.get("response", "")
    has_html = result_data.get("has_html", False)
    has_images = result_data.get("has_images", False)
    error = result_data.get("error")

    user_prompt = (
        f"## Test Input\nTask: {test_input['task']}\n"
        f"Context: {test_input.get('context', 'N/A')}\n\n"
        f"## Agent Result\n"
        f"Success: {result_data.get('success', 'unknown')}\n"
        f"Tools used: {', '.join(tools_used) if tools_used else 'none'}\n"
        f"Generated HTML: {'yes' if has_html else 'no'}\n"
        f"Generated images: {'yes' if has_images else 'no'}\n"
        f"Error: {error or 'none'}\n"
        f"Response: {response_text[:1000]}\n\n"
        f"## Criteria to evaluate\n{criteria_list}\n\n"
        "Evaluate each criterion. Return JSON only."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        raw = await call_llm(
            llm_url=llm_url, model=model, messages=messages,
            temperature=0.0, provider_type=provider_type, api_key=api_key,
        )
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        parsed = json.loads(text)
        parsed["examiner_model"] = model
        return parsed
    except Exception as e:
        logger.error(f"Examiner LLM error: {e}")
        return {
            "overall": "error",
            "criteria_results": [],
            "error": str(e),
            "examiner_model": model,
        }


def _persist_execution(agent_id: str, test_id: str, execution: Dict[str, Any]) -> None:
    """Save execution summary alongside manual results in _results.json."""
    results = _load_test_results(agent_id)
    entry = results.get(test_id, {})
    entry["lastExecution"] = execution
    results[test_id] = entry
    _save_test_results(agent_id, results)


def _save_test_results(agent_id: str, results: Dict[str, Any]) -> None:
    """Overwrite the full _results.json file."""
    import json
    from pathlib import Path
    results_file = Path(__file__).parent / agent_id.replace("_agent", "") / "tests" / "_results.json"
    try:
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving test results: {e}")


def _extract_test_artifacts(result_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Extract HTML, artifact URLs from nested tool_results for test display."""
    html = None
    artifact_urls: List[Dict[str, str]] = []

    tool_results = (result_dict.get("data") or {}).get("tool_results", [])
    for tr in tool_results:
        raw = tr.get("result") or {}
        if not isinstance(raw, dict):
            continue
        if raw.get("html") and not html:
            html = raw["html"]
        if raw.get("artifact_id"):
            artifact_urls.append({
                "id": raw["artifact_id"],
                "url": f"/api/v1/artifacts/{raw['artifact_id']}/content",
                "type": raw.get("artifact_type") or raw.get("mime_type", "file"),
                "title": raw.get("title", tr.get("tool", "")),
            })

    for img in result_dict.get("images", []):
        if img.get("url") and "/artifacts/" in str(img["url"]):
            aid = img["url"].split("/artifacts/")[1].split("/")[0]
            if not any(a["id"] == aid for a in artifact_urls):
                artifact_urls.append({
                    "id": aid,
                    "url": img["url"],
                    "type": "image",
                    "title": img.get("alt_text", "Image"),
                })

    return {"html": html, "artifact_urls": artifact_urls}


# ============================================
# Helpers
# ============================================

def _get_agent_icon(agent_id: str) -> str:
    """Retorna el icono para un subagente (primero del registro, fallback estatico)."""
    agent = subagent_registry.get(agent_id)
    if agent and getattr(agent, "icon", None):
        return agent.icon
    fallback = {
        "designer_agent": "palette",
        "researcher_agent": "search",
        "communication_agent": "campaign",
        "rag_agent": "menu_book",
        "sap_analyst": "analytics",
    }
    return fallback.get(agent_id, "smart_toy")


async def _get_agent_config(agent_id: str) -> Dict[str, Any]:
    """Obtiene configuración de un subagente desde PostgreSQL o retorna defaults"""
    from src.db.repositories import SubagentConfigRepository
    
    try:
        # Buscar configuración guardada en BD
        db_config = await SubagentConfigRepository.get_by_agent_id(agent_id)
        
        if db_config:
            return {
                "enabled": db_config.is_enabled,
                "llm_provider": db_config.llm_provider_id,
                "llm_model": db_config.llm_model,
                "system_prompt": db_config.system_prompt,
                "settings": db_config.settings or {}
            }
    except Exception as e:
        logger.warning(f"Error loading config from DB for {agent_id}: {e}")
    
    # Defaults si no hay configuración en BD
    base_config = {
        "enabled": True,
        "llm_provider": None,  # Null = usar provider por defecto
        "llm_model": None,  # Null = usar modelo por defecto del provider
        "system_prompt": None,
        "settings": {}
    }
    
    # Configuraciones específicas por agente (defaults)
    default_configs = {
        "designer_agent": {
            **base_config,
            "settings": {}
        },
        "researcher_agent": {
            **base_config,
            "settings": {
                "search_depth": "comprehensive"
            }
        },
        "communication_agent": {
            **base_config,
            "settings": {
                "default_tone": "professional"
            }
        }
    }
    
    return default_configs.get(agent_id, base_config)


async def _resolve_llm_provider(provider_id: int) -> Optional[Dict[str, Any]]:
    """
    Resuelve un provider ID a su configuración completa desde la BD.
    
    Args:
        provider_id: ID del provider en llm_providers
        
    Returns:
        Dict con base_url, default_model, type, api_key o None si no existe
    """
    try:
        from src.db.repositories import LLMProviderRepository
        
        provider = await LLMProviderRepository.get_by_id(provider_id)
        
        if not provider:
            logger.warning(f"Provider {provider_id} not found in database")
            return None
        
        return {
            "id": provider.id,
            "base_url": provider.base_url,
            "default_model": provider.default_model,
            "type": provider.type or "ollama",
            "api_key": provider.api_key,
            "name": provider.name
        }
            
    except Exception as e:
        logger.error(f"Error resolving provider {provider_id}: {e}")
        return None
