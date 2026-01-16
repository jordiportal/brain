"""
Router para herramientas (OpenAPI, builtin, etc.)
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from .openapi_tools import openapi_toolkit
from .tool_registry import tool_registry, ToolType

router = APIRouter(prefix="/tools", tags=["Tools"])


class ConnectionCreate(BaseModel):
    """Request para crear una conexión OpenAPI"""
    name: str
    specUrl: str
    baseUrl: str
    authType: str = "none"
    authToken: Optional[str] = None
    authHeader: str = "Authorization"
    authPrefix: str = "Bearer"
    timeout: int = 30000
    customHeaders: Optional[Dict[str, str]] = None


class ToolExecuteRequest(BaseModel):
    """Request para ejecutar una herramienta"""
    tool_id: str
    parameters: Dict[str, Any] = {}


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


@router.post("/openapi/connections")
async def add_openapi_connection(connection: ConnectionCreate):
    """Añade una conexión OpenAPI (sin persistir en Strapi)"""
    conn_id = await openapi_toolkit.add_connection(
        name=connection.name,
        spec_url=connection.specUrl,
        base_url=connection.baseUrl,
        auth_type=connection.authType,
        auth_token=connection.authToken,
        auth_header=connection.authHeader,
        auth_prefix=connection.authPrefix,
        timeout=connection.timeout,
        custom_headers=connection.customHeaders
    )
    
    return {
        "status": "ok",
        "message": f"Conexión '{connection.name}' añadida",
        "connection_id": conn_id
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
# Herramientas
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


@router.post("/execute")
async def execute_tool_by_request(request: ToolExecuteRequest):
    """Ejecuta una herramienta (alternativa)"""
    return await execute_tool(request.tool_id, request.parameters)


# ============================================
# Utilidades
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
