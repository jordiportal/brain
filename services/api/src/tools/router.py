"""
Router para herramientas (OpenAPI, builtin, etc.)

Incluye endpoints para:
- Conexiones OpenAPI
- Listado y ejecución de herramientas
- Configuración de herramientas (schemas dinámicos)

IMPORTANTE: El orden de las rutas importa en FastAPI.
Las rutas específicas deben ir ANTES de las rutas con parámetros.
"""

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Body, Query
from pydantic import BaseModel
import structlog

from .openapi_tools import openapi_toolkit
from .tool_registry import tool_registry, ToolType
from .schemas import configurable_tools_registry

logger = structlog.get_logger()

router = APIRouter(prefix="/tools", tags=["Tools"])


class ToolExecuteRequest(BaseModel):
    """Request para ejecutar una herramienta"""
    tool_id: str
    parameters: Dict[str, Any] = {}


# ============================================
# Configuración de Herramientas - Funciones auxiliares
# ============================================

# Archivo de configuración de herramientas
TOOLS_CONFIG_FILE = Path(__file__).parent.parent / "config" / "tools_config.json"


def _ensure_config_dir():
    """Asegura que el directorio de config existe"""
    TOOLS_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_tools_config() -> Dict[str, Any]:
    """Carga la configuración de herramientas desde archivo"""
    _ensure_config_dir()
    
    if not TOOLS_CONFIG_FILE.exists():
        return {}
    
    try:
        with open(TOOLS_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading tools config: {e}")
        return {}


def _save_tools_config(configs: Dict[str, Any]) -> None:
    """Guarda la configuración de herramientas"""
    _ensure_config_dir()
    
    try:
        with open(TOOLS_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(configs, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving tools config: {e}")
        raise


# ============================================
# Conexiones OpenAPI
# ============================================

@router.get("/openapi/connections")
async def list_openapi_connections():
    """Lista todas las conexiones OpenAPI configuradas"""
    # Cargar desde Strapi si no están cargadas
    if not openapi_toolkit.connections:
        await openapi_toolkit.load_connections_from_strapi()
    
    return {
        "connections": [
            {
                "id": conn["id"],
                "name": conn["name"],
                "slug": conn["slug"],
                "specUrl": conn["specUrl"],
                "baseUrl": conn["baseUrl"],
                "authType": conn["authType"],
                "hasAuth": bool(conn.get("authToken")),
                "timeout": conn["timeout"]
            }
            for conn in openapi_toolkit.connections.values()
        ],
        "total": len(openapi_toolkit.connections)
    }


@router.post("/openapi/connections/refresh")
async def refresh_openapi_connections():
    """Recarga las conexiones OpenAPI desde Strapi"""
    count = await openapi_toolkit.refresh_connections()
    
    return {
        "status": "ok",
        "message": f"Recargadas {count} conexiones desde Strapi",
        "count": count
    }


@router.get("/openapi/connections/{connection_id}/spec")
async def get_connection_spec(connection_id: str):
    """Obtiene la especificación OpenAPI de una conexión"""
    try:
        spec = await openapi_toolkit.fetch_and_parse_spec(connection_id)
        return {
            "connection_id": connection_id,
            "spec": {
                "info": spec.get("info", {}),
                "paths_count": len(spec.get("paths", {})),
                "schemas_count": len(spec.get("components", {}).get("schemas", {}))
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/openapi/connections/{connection_id}/generate-tools")
async def generate_tools_for_connection(connection_id: str):
    """Genera herramientas desde una conexión OpenAPI"""
    try:
        tools = await openapi_toolkit.generate_tools(connection_id)
        
        # Registrar en el registry global
        for tool in tools:
            tool_registry.register_openapi_tool(tool)
        
        return {
            "status": "ok",
            "message": f"Generadas {len(tools)} herramientas",
            "connection_id": connection_id,
            "tools": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "method": t.method,
                    "path": t.path
                }
                for t in tools
            ]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Herramientas Configurables - Schemas Dinámicos
# (IMPORTANTE: Estas rutas específicas van ANTES de /{tool_id})
# ============================================

@router.get("/configurable")
async def list_configurable_tools(
    include_admin: bool = Query(False, description="Incluir herramientas solo para administradores"),
    category: Optional[str] = Query(None, description="Filtrar por categoría (media, web, execution, ai)")
):
    """
    Lista todas las herramientas configurables con sus schemas.
    
    Devuelve la información necesaria para que el frontend renderice
    dinámicamente los formularios de configuración.
    
    Args:
        include_admin: Si True, incluye herramientas admin_only
        category: Filtrar por categoría
        
    Returns:
        Lista de herramientas con su config_schema completo
    """
    if category:
        schemas = configurable_tools_registry.get_by_category(category, include_admin)
    else:
        schemas = configurable_tools_registry.get_all(include_admin)
    
    # Cargar configuraciones guardadas
    saved_configs = _load_tools_config()
    
    # Combinar schemas con configuraciones guardadas
    result = []
    for schema in schemas:
        tool_data = schema.to_dict()
        
        # Mezclar config guardada con defaults
        if schema.id in saved_configs:
            tool_data["config"] = {
                **schema.default_config,
                **saved_configs[schema.id]
            }
        else:
            tool_data["config"] = schema.default_config.copy()
        
        result.append(tool_data)
    
    return {
        "tools": result,
        "count": len(result),
        "categories": configurable_tools_registry.get_categories()
    }


@router.get("/configurable/categories")
async def list_tool_categories():
    """Lista las categorías disponibles de herramientas configurables"""
    return {
        "categories": configurable_tools_registry.get_categories()
    }


@router.get("/configurable/{tool_id}")
async def get_configurable_tool(tool_id: str):
    """
    Obtiene el schema de configuración de una herramienta específica.
    
    Args:
        tool_id: ID de la herramienta
        
    Returns:
        Schema completo con config_schema y configuración actual
    """
    schema = configurable_tools_registry.get(tool_id)
    
    if not schema:
        raise HTTPException(
            status_code=404, 
            detail=f"Herramienta configurable no encontrada: {tool_id}"
        )
    
    # Cargar configuración guardada
    saved_configs = _load_tools_config()
    
    tool_data = schema.to_dict()
    
    # Mezclar config guardada con defaults
    if tool_id in saved_configs:
        tool_data["config"] = {
            **schema.default_config,
            **saved_configs[tool_id]
        }
    else:
        tool_data["config"] = schema.default_config.copy()
    
    return tool_data


@router.get("/configurable/{tool_id}/schema")
async def get_tool_config_schema(tool_id: str):
    """
    Obtiene solo el schema de configuración (sin los valores actuales).
    
    Útil para validación o cuando solo necesitas la estructura.
    
    Args:
        tool_id: ID de la herramienta
        
    Returns:
        config_schema con campos y sus metadatos
    """
    schema = configurable_tools_registry.get(tool_id)
    
    if not schema:
        raise HTTPException(
            status_code=404, 
            detail=f"Herramienta configurable no encontrada: {tool_id}"
        )
    
    return {
        "tool_id": tool_id,
        "display_name": schema.display_name,
        "config_schema": [f.to_dict() for f in schema.config_schema],
        "default_config": schema.default_config
    }


# ============================================
# Configuración de Herramientas Core (legacy endpoints)
# (IMPORTANTE: Estas rutas específicas van ANTES de /{tool_id})
# ============================================

@router.get("/config")
async def get_tools_config():
    """Obtiene la configuración de todas las herramientas core"""
    configs = _load_tools_config()
    
    return {
        "configs": configs,
        "count": len(configs)
    }


@router.get("/config/{tool_id}")
async def get_tool_config(tool_id: str):
    """Obtiene la configuración de una herramienta específica"""
    configs = _load_tools_config()
    
    if tool_id not in configs:
        # Devolver configuración vacía si no existe
        return {
            "tool_id": tool_id,
            "config": {}
        }
    
    return {
        "tool_id": tool_id,
        "config": configs[tool_id]
    }


@router.put("/config/{tool_id}")
async def update_tool_config(tool_id: str, config: Dict[str, Any] = Body(...)):
    """Actualiza la configuración de una herramienta"""
    configs = _load_tools_config()
    
    # Actualizar config
    configs[tool_id] = config
    
    # Guardar
    _save_tools_config(configs)
    
    logger.info(f"🔧 Tool config updated: {tool_id}", config=config)
    
    return {
        "status": "ok",
        "tool_id": tool_id,
        "config": config
    }


# ============================================
# Utilidades
# (IMPORTANTE: Estas rutas específicas van ANTES de /{tool_id})
# ============================================

@router.post("/load-all")
async def load_all_tools():
    """Carga todas las herramientas (builtin + OpenAPI desde Strapi)"""
    tool_registry.register_builtin_tools()
    
    openapi_count = await tool_registry.load_openapi_tools()
    
    return {
        "status": "ok",
        "message": "Herramientas cargadas",
        "builtin_tools": len([t for t in tool_registry.list() if t.type == ToolType.BUILTIN]),
        "openapi_tools": openapi_count,
        "total": len(tool_registry.tools)
    }


@router.get("/for-llm")
async def get_tools_for_llm(tool_ids: Optional[str] = None):
    """Obtiene las herramientas en formato para el LLM"""
    ids = tool_ids.split(",") if tool_ids else None
    
    schemas = tool_registry.get_tools_for_llm(ids)
    
    return {
        "tools": schemas,
        "count": len(schemas)
    }


@router.post("/execute")
async def execute_tool_by_request(request: ToolExecuteRequest):
    """Ejecuta una herramienta (alternativa)"""
    return await execute_tool(request.tool_id, request.parameters)


# ============================================
# Herramientas - Rutas con parámetros
# (IMPORTANTE: Estas rutas van AL FINAL porque capturan cualquier path)
# ============================================

@router.get("")
async def list_tools(type: Optional[str] = None, connection_id: Optional[str] = None):
    """Lista todas las herramientas disponibles"""
    # Registrar builtin si no están
    tool_registry.register_builtin_tools()
    
    # Filtrar por tipo si se especifica
    tool_type = None
    if type:
        try:
            tool_type = ToolType(type)
        except:
            pass
    
    tools = tool_registry.list(tool_type)
    
    # Filtrar por conexión si se especifica
    if connection_id:
        tools = [t for t in tools if t.openapi_tool and t.openapi_tool.connection_id == connection_id]
    
    return {
        "tools": [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "type": t.type.value,
                "connection_id": t.openapi_tool.connection_id if t.openapi_tool else None
            }
            for t in tools
        ],
        "total": len(tools)
    }


@router.get("/{tool_id}")
async def get_tool(tool_id: str):
    """Obtiene detalles de una herramienta"""
    tool = tool_registry.get(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Herramienta no encontrada: {tool_id}")
    
    return {
        "tool": {
            "id": tool.id,
            "name": tool.name,
            "description": tool.description,
            "type": tool.type.value,
            "parameters": tool.to_function_schema().get("parameters", {}),
            "connection_id": tool.openapi_tool.connection_id if tool.openapi_tool else None,
            "method": tool.openapi_tool.method if tool.openapi_tool else None,
            "path": tool.openapi_tool.path if tool.openapi_tool else None
        }
    }


@router.get("/{tool_id}/schema")
async def get_tool_schema(tool_id: str):
    """Obtiene el schema de función de una herramienta (para LLM)"""
    tool = tool_registry.get(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Herramienta no encontrada: {tool_id}")
    
    return tool.to_function_schema()


@router.post("/{tool_id}/execute")
async def execute_tool(tool_id: str, parameters: Dict[str, Any] = Body(default={})):
    """Ejecuta una herramienta con los parámetros dados"""
    tool = tool_registry.get(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Herramienta no encontrada: {tool_id}")
    
    result = await tool_registry.execute(tool_id, **parameters)
    
    return {
        "tool_id": tool_id,
        "parameters": parameters,
        "result": result
    }
