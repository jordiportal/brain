"""
Router para gestión de Subagentes Especializados

Endpoints para listar, configurar y probar subagentes.
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
import structlog

from . import subagent_registry, register_all_subagents

logger = structlog.get_logger()

router = APIRouter(prefix="/subagents", tags=["Subagents"])


class SubagentExecuteRequest(BaseModel):
    """Request para ejecutar una tarea en un subagente"""
    task: str
    context: Optional[str] = None
    llm_url: Optional[str] = None
    model: Optional[str] = None
    provider_type: str = "ollama"
    api_key: Optional[str] = None


class SubagentConfigUpdate(BaseModel):
    """Request para actualizar configuración de un subagente"""
    enabled: bool = True
    system_prompt: Optional[str] = None
    default_provider: Optional[str] = None
    default_model: Optional[str] = None
    settings: Dict[str, Any] = {}


# ============================================
# Listar y Obtener Subagentes
# ============================================

@router.get("")
async def list_subagents():
    """Lista todos los subagentes registrados"""
    # Asegurar que los subagentes estén registrados
    if not subagent_registry.is_initialized():
        register_all_subagents()
    
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


@router.get("/{agent_id}")
async def get_subagent(agent_id: str):
    """Obtiene detalles de un subagente específico"""
    if not subagent_registry.is_initialized():
        register_all_subagents()
    
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Subagente no encontrado: {agent_id}"
        )
    
    # Obtener herramientas del agente
    tools = agent.get_tools()
    
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
        register_all_subagents()
    
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
    
    Útil para probar subagentes directamente sin pasar por el Adaptive Agent.
    """
    if not subagent_registry.is_initialized():
        register_all_subagents()
    
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Subagente no encontrado: {agent_id}"
        )
    
    logger.info(
        f"🎯 Direct execution of subagent",
        agent_id=agent_id,
        task=request.task[:100]
    )
    
    try:
        result = await agent.execute(
            task=request.task,
            context=request.context,
            llm_url=request.llm_url,
            model=request.model,
            provider_type=request.provider_type,
            api_key=request.api_key
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


@router.post("/{agent_id}/test")
async def test_subagent(agent_id: str):
    """
    Prueba rápida de un subagente.
    
    Verifica que el subagente está correctamente configurado y sus tools funcionan.
    """
    if not subagent_registry.is_initialized():
        register_all_subagents()
    
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
    """Obtiene la configuración actual de un subagente"""
    if not subagent_registry.is_initialized():
        register_all_subagents()
    
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Subagente no encontrado: {agent_id}"
        )
    
    # TODO: Cargar configuración desde Strapi
    config = _get_agent_config(agent_id)
    
    # Añadir system_prompt del agente
    config["system_prompt"] = agent.system_prompt
    
    return {
        "agent_id": agent_id,
        "config": config
    }


@router.put("/{agent_id}/config")
async def update_subagent_config(agent_id: str, config: SubagentConfigUpdate):
    """Actualiza la configuración de un subagente"""
    if not subagent_registry.is_initialized():
        register_all_subagents()
    
    agent = subagent_registry.get(agent_id)
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Subagente no encontrado: {agent_id}"
        )
    
    # Actualizar system_prompt si se proporciona
    if config.system_prompt is not None:
        agent.system_prompt = config.system_prompt
        logger.info(
            f"📝 Updated system_prompt for {agent_id}",
            prompt_length=len(config.system_prompt)
        )
    
    # TODO: Guardar configuración completa en Strapi
    logger.info(
        f"📝 Updating subagent config",
        agent_id=agent_id,
        enabled=config.enabled
    )
    
    return {
        "status": "ok",
        "message": f"Configuración de {agent_id} actualizada",
        "agent_id": agent_id,
        "updated": {
            "system_prompt": config.system_prompt is not None,
            "enabled": config.enabled
        }
    }


# ============================================
# Skills de Subagentes
# ============================================

@router.get("/{agent_id}/skills")
async def get_subagent_skills(agent_id: str):
    """Obtiene los skills disponibles de un subagente"""
    if not subagent_registry.is_initialized():
        register_all_subagents()
    
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
        register_all_subagents()
    
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
        register_all_subagents()
    
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


@router.get("/{agent_id}/tests")
async def get_subagent_tests(agent_id: str):
    """Obtiene los tests definidos para un subagente"""
    if not subagent_registry.is_initialized():
        register_all_subagents()
    
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
        register_all_subagents()
    
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
        # Ejecutar el subagente con el input del test
        result = await agent.execute(
            task=test["input"]["task"],
            context=test["input"].get("context"),
            llm_url=llm_url,
            model=model,
            provider_type=provider_type,
            api_key=api_key
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return {
            "agent_id": agent_id,
            "test_id": test_id,
            "test_name": test["name"],
            "status": "executed",
            "duration_ms": duration_ms,
            "result": result.to_dict(),
            "expected": test["expected"],
            "criteria": test["expected"].get("criteria", [])
        }
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Test execution error: {e}", exc_info=True)
        
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
    from datetime import datetime
    
    if not subagent_registry.is_initialized():
        register_all_subagents()
    
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
    """Guarda el resultado de un test"""
    import json
    from pathlib import Path
    
    results_file = Path(__file__).parent / agent_id.replace("_agent", "") / "tests" / "_results.json"
    
    # Cargar resultados existentes
    results = _load_test_results(agent_id)
    
    # Actualizar
    results[test_id] = result
    
    # Guardar
    try:
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving test result: {e}")


# ============================================
# Helpers
# ============================================

def _get_agent_icon(agent_id: str) -> str:
    """Retorna el icono para un subagente"""
    icons = {
        "designer_agent": "palette",
        "researcher_agent": "search",
        "communication_agent": "campaign",
        "sap_agent": "business",
        "mail_agent": "email",
        "office_agent": "description"
    }
    return icons.get(agent_id, "smart_toy")


def _get_agent_config(agent_id: str) -> Dict[str, Any]:
    """Obtiene configuración de un subagente (placeholder para Strapi)"""
    # TODO: Implementar lectura desde Strapi
    default_configs = {
        "designer_agent": {
            "enabled": True,
            "default_provider": "openai",
            "default_model": "dall-e-3",
            "default_size": "1024x1024",
            "max_concurrent": 3,
            "settings": {
                "quality": "standard",
                "style": "vivid"
            }
        }
    }
    
    return default_configs.get(agent_id, {
        "enabled": True,
        "settings": {}
    })
