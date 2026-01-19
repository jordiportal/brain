"""
MCP Router - Endpoints para gestionar conexiones MCP
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import structlog

from .client import mcp_client
from .models import MCPConnection, MCPConnectionType

logger = structlog.get_logger()

router = APIRouter(prefix="/mcp", tags=["MCP"])


# ===== Modelos de Request/Response =====

class MCPConnectionCreate(BaseModel):
    """Request para crear una conexión MCP"""
    name: str
    type: str = "stdio"
    description: str = ""
    command: Optional[str] = None
    args: List[str] = []
    env: Dict[str, str] = {}
    server_url: Optional[str] = None
    config: Dict[str, Any] = {}


class MCPToolCallRequest(BaseModel):
    """Request para llamar a una herramienta MCP"""
    connection_id: str
    tool_name: str
    arguments: Dict[str, Any] = {}


class MCPResourceReadRequest(BaseModel):
    """Request para leer un recurso MCP"""
    connection_id: str
    uri: str


# ===== Endpoints =====

@router.get("/connections")
async def list_connections():
    """Listar todas las conexiones MCP"""
    return {
        "connections": mcp_client.list_connections()
    }


@router.post("/connections/load")
async def load_connections_from_strapi():
    """Cargar conexiones desde Strapi"""
    count = await mcp_client.load_connections_from_strapi()
    return {
        "loaded": count,
        "connections": mcp_client.list_connections()
    }


@router.post("/connections")
async def create_connection(request: MCPConnectionCreate):
    """Crear una nueva conexión MCP (en memoria, no persiste en Strapi)"""
    import uuid
    
    connection = MCPConnection(
        id=str(uuid.uuid4()),
        name=request.name,
        conn_type=MCPConnectionType(request.type),
        description=request.description,
        command=request.command,
        args=request.args,
        env=request.env,
        server_url=request.server_url,
        config=request.config
    )
    
    conn_id = await mcp_client.register_connection(connection)
    
    return {
        "id": conn_id,
        "name": connection.name,
        "message": "Conexión creada. Use /connect para conectar."
    }


@router.post("/connections/{connection_id}/connect")
async def connect_to_mcp(connection_id: str):
    """Conectar a un servidor MCP"""
    connection = mcp_client.get_connection(connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Conexión no encontrada")
    
    success = await mcp_client.connect(connection_id)
    
    if success:
        return {
            "connected": True,
            "name": connection.name,
            "server_info": connection.server_info,
            "tools": [
                {"name": t.name, "description": t.description}
                for t in connection.tools
            ],
            "resources": [
                {"uri": r.uri, "name": r.name}
                for r in connection.resources
            ]
        }
    else:
        raise HTTPException(
            status_code=500, 
            detail=f"No se pudo conectar a {connection.name}"
        )


@router.post("/connections/{connection_id}/disconnect")
async def disconnect_from_mcp(connection_id: str):
    """Desconectar de un servidor MCP"""
    connection = mcp_client.get_connection(connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Conexión no encontrada")
    
    await mcp_client.disconnect(connection_id)
    
    return {"disconnected": True, "name": connection.name}


@router.get("/connections/{connection_id}/tools")
async def get_connection_tools(connection_id: str):
    """Obtener herramientas de una conexión MCP"""
    connection = mcp_client.get_connection(connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Conexión no encontrada")
    
    if not connection.is_connected:
        # Intentar conectar
        await mcp_client.connect(connection_id)
    
    return {
        "connection": connection.name,
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema
            }
            for t in connection.tools
        ]
    }


@router.get("/connections/{connection_id}/resources")
async def get_connection_resources(connection_id: str):
    """Obtener recursos de una conexión MCP"""
    connection = mcp_client.get_connection(connection_id)
    if not connection:
        raise HTTPException(status_code=404, detail="Conexión no encontrada")
    
    if not connection.is_connected:
        await mcp_client.connect(connection_id)
    
    return {
        "connection": connection.name,
        "resources": [
            {
                "uri": r.uri,
                "name": r.name,
                "description": r.description,
                "mime_type": r.mime_type
            }
            for r in connection.resources
        ]
    }


@router.post("/tools/call")
async def call_mcp_tool(request: MCPToolCallRequest):
    """Llamar a una herramienta MCP"""
    result = await mcp_client.call_tool(
        request.connection_id,
        request.tool_name,
        request.arguments
    )
    
    if not result.get("success", False) and result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@router.post("/resources/read")
async def read_mcp_resource(request: MCPResourceReadRequest):
    """Leer un recurso MCP"""
    result = await mcp_client.read_resource(
        request.connection_id,
        request.uri
    )
    
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "Error leyendo recurso"))
    
    return result


@router.get("/tools")
async def get_all_mcp_tools():
    """Obtener todas las herramientas de todas las conexiones MCP conectadas"""
    all_tools = mcp_client.get_all_tools()
    
    result = []
    for conn_id, tools in all_tools.items():
        connection = mcp_client.get_connection(conn_id)
        for tool in tools:
            result.append({
                "connection_id": conn_id,
                "connection_name": connection.name if connection else "",
                "tool_name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema
            })
    
    return {"tools": result}
