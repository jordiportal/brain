"""
MCP Client - Cliente para conectar con servidores MCP (Model Context Protocol)

Implementa el protocolo JSON-RPC 2.0 sobre STDIO y HTTP para comunicarse con servidores MCP.
"""

import asyncio
import json
import os
import subprocess
import uuid
from typing import Optional, Dict, Any, List
import httpx
import structlog

from .models import MCPConnection, MCPConnectionType, MCPTool, MCPResource

logger = structlog.get_logger()

# Configuración de Strapi
STRAPI_URL = os.getenv("STRAPI_URL", "http://localhost:1337")
STRAPI_API_TOKEN = os.getenv("STRAPI_API_TOKEN", "")

# URL del servidor MCP Playwright (para conexión HTTP)
MCP_PLAYWRIGHT_URL = os.getenv("MCP_PLAYWRIGHT_URL", "http://localhost:3001")


class MCPClient:
    """
    Cliente para gestionar conexiones MCP.
    
    Soporta:
    - Conexiones STDIO (subprocesos)
    - Conexiones HTTP/SSE con sesiones persistentes
    """
    
    def __init__(self):
        self.connections: Dict[str, MCPConnection] = {}
        self._request_id = 0
        self._locks: Dict[str, asyncio.Lock] = {}
        self._http_clients: Dict[str, httpx.AsyncClient] = {}  # Clientes HTTP persistentes
    
    async def load_connections_from_strapi(self) -> int:
        """Cargar conexiones activas desde Strapi"""
        try:
            headers = {}
            if STRAPI_API_TOKEN:
                headers["Authorization"] = f"Bearer {STRAPI_API_TOKEN}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{STRAPI_URL}/api/mcp-connections",
                    params={"filters[isActive][$eq]": "true"},
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    count = 0
                    
                    for item in data.get("data", []):
                        connection = MCPConnection.from_strapi(item)
                        self.connections[connection.id] = connection
                        self._locks[connection.id] = asyncio.Lock()
                        count += 1
                    
                    logger.info(f"Cargadas {count} conexiones MCP desde Strapi")
                    return count
                else:
                    logger.warning(f"Error cargando conexiones MCP: {response.status_code}")
                    return 0
                    
        except Exception as e:
            logger.error(f"Error conectando con Strapi para MCP: {e}")
            return 0
    
    async def connect(self, connection_id: str) -> bool:
        """Conectar a un servidor MCP"""
        connection = self.connections.get(connection_id)
        if not connection:
            logger.error(f"Conexión MCP no encontrada: {connection_id}")
            return False
        
        if connection.is_connected:
            logger.info(f"MCP {connection.name} ya está conectado")
            return True
        
        if connection.conn_type == MCPConnectionType.STDIO:
            return await self._connect_stdio(connection)
        elif connection.conn_type in (MCPConnectionType.HTTP, MCPConnectionType.SSE):
            return await self._connect_http(connection)
        else:
            logger.error(f"Tipo de conexión MCP no soportado: {connection.conn_type}")
            return False
    
    async def _connect_stdio(self, connection: MCPConnection) -> bool:
        """Conectar a un servidor MCP via STDIO"""
        try:
            if not connection.command:
                logger.error(f"MCP {connection.name}: comando no especificado")
                return False
            
            # Preparar entorno
            env = {**dict(os.environ), **connection.env}
            
            # Construir comando
            cmd = [connection.command] + connection.args
            logger.info(f"Iniciando MCP: {' '.join(cmd)}")
            
            # Iniciar el proceso del servidor MCP
            connection.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                bufsize=0  # Sin buffering
            )
            
            # Pequeña pausa para que el servidor arranque
            await asyncio.sleep(0.5)
            
            # Verificar que el proceso está corriendo
            if connection.process.poll() is not None:
                stderr = connection.process.stderr.read().decode() if connection.process.stderr else ""
                logger.error(f"MCP {connection.name} terminó inesperadamente: {stderr}")
                return False
            
            # Enviar initialize request
            init_response = await self._send_request(
                connection,
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "roots": {"listChanged": True},
                        "sampling": {}
                    },
                    "clientInfo": {
                        "name": "brain-api",
                        "version": "1.0.0"
                    }
                }
            )
            
            if init_response.get("error"):
                logger.error(f"Error inicializando MCP {connection.name}: {init_response['error']}")
                return False
            
            if init_response.get("result"):
                connection.server_info = init_response["result"].get("serverInfo", {})
                connection.is_connected = True
                
                # Enviar initialized notification
                await self._send_notification(connection, "notifications/initialized", {})
                
                # Obtener lista de herramientas
                tools_response = await self._send_request(connection, "tools/list", {})
                if tools_response.get("result", {}).get("tools"):
                    connection.tools = [
                        MCPTool(
                            name=t["name"],
                            description=t.get("description", ""),
                            input_schema=t.get("inputSchema", {})
                        )
                        for t in tools_response["result"]["tools"]
                    ]
                
                # Obtener lista de recursos (opcional)
                try:
                    resources_response = await self._send_request(connection, "resources/list", {})
                    if resources_response.get("result", {}).get("resources"):
                        connection.resources = [
                            MCPResource(
                                uri=r["uri"],
                                name=r.get("name", ""),
                                description=r.get("description", ""),
                                mime_type=r.get("mimeType", "text/plain")
                            )
                            for r in resources_response["result"]["resources"]
                        ]
                except Exception:
                    pass  # Recursos es opcional
                
                logger.info(
                    f"Conectado a MCP: {connection.name}",
                    server=connection.server_info.get("name"),
                    tools=len(connection.tools),
                    resources=len(connection.resources)
                )
                return True
            
            return False
                
        except Exception as e:
            logger.error(f"Error conectando MCP {connection.name}: {e}")
            if connection.process:
                connection.process.terminate()
                connection.process = None
            return False
    
    async def _connect_http(self, connection: MCPConnection) -> bool:
        """Conectar a un servidor MCP via HTTP con cliente persistente"""
        try:
            if not connection.server_url:
                logger.error(f"MCP {connection.name}: URL del servidor no especificada")
                return False
            
            base_url = connection.server_url.rstrip('/')
            headers = {
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json"
            }
            
            # Crear cliente HTTP persistente para esta conexión
            if connection.id in self._http_clients:
                await self._http_clients[connection.id].aclose()
            
            client = httpx.AsyncClient(
                timeout=60.0,
                headers=headers,
                http2=False  # Usar HTTP/1.1 para mejor compatibilidad
            )
            self._http_clients[connection.id] = client
            
            # Inicializar conexión MCP via HTTP
            init_response = await client.post(
                f"{base_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "brain-api",
                            "version": "1.0.0"
                        }
                    }
                }
            )
            
            if init_response.status_code == 200:
                # Parsear respuesta SSE
                init_data = self._parse_sse_response(init_response.text)
                
                if init_data and init_data.get("result"):
                    connection.server_info = init_data["result"].get("serverInfo", {})
                    connection.is_connected = True
                    
                    # Obtener herramientas usando el mismo cliente
                    tools_response = await client.post(
                        f"{base_url}/mcp",
                        json={
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "tools/list",
                            "params": {}
                        }
                    )
                    
                    if tools_response.status_code == 200:
                        tools_data = self._parse_sse_response(tools_response.text)
                        if tools_data and tools_data.get("result", {}).get("tools"):
                            connection.tools = [
                                MCPTool(
                                    name=t["name"],
                                    description=t.get("description", ""),
                                    input_schema=t.get("inputSchema", {})
                                )
                                for t in tools_data["result"]["tools"]
                            ]
                        else:
                            logger.warning(f"MCP {connection.name}: No se obtuvieron herramientas: {tools_data}")
                    
                    logger.info(
                        f"Conectado a MCP (HTTP): {connection.name}",
                        server=connection.server_info.get("name"),
                        tools=len(connection.tools)
                    )
                    return True
                else:
                    error = init_data.get("error", {}) if init_data else "Sin respuesta"
                    logger.error(f"Error inicializando MCP {connection.name}: {error}")
                    await client.aclose()
                    del self._http_clients[connection.id]
                    return False
            else:
                logger.error(f"MCP {connection.name} respondió con {init_response.status_code}: {init_response.text[:200]}")
                await client.aclose()
                del self._http_clients[connection.id]
                return False
                    
        except httpx.ConnectError as e:
            logger.error(f"No se pudo conectar a MCP {connection.name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error conectando MCP HTTP {connection.name}: {e}")
            return False
    
    def _parse_sse_response(self, content: str) -> Optional[Dict[str, Any]]:
        """Parsear respuesta SSE o JSON"""
        # Buscar líneas que empiecen con "data:"
        for line in content.split('\n'):
            if line.startswith('data:'):
                data_str = line[5:].strip()
                if data_str:
                    try:
                        return json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
        
        # Si no es SSE, intentar parsear como JSON directo
        try:
            return json.loads(content)
        except Exception:
            return None
    
    async def _send_request(
        self, 
        connection: MCPConnection, 
        method: str, 
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enviar request JSON-RPC al servidor MCP"""
        self._request_id += 1
        
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params
        }
        
        lock = self._locks.get(connection.id)
        if lock:
            async with lock:
                return await self._send_and_receive(connection, request)
        else:
            return await self._send_and_receive(connection, request)
    
    async def _send_notification(
        self,
        connection: MCPConnection,
        method: str,
        params: Dict[str, Any]
    ):
        """Enviar notificación JSON-RPC (sin esperar respuesta)"""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        
        if connection.process and connection.process.stdin:
            try:
                request_str = json.dumps(notification) + "\n"
                connection.process.stdin.write(request_str.encode())
                connection.process.stdin.flush()
            except Exception as e:
                logger.error(f"Error enviando notificación MCP: {e}")
    
    async def _send_and_receive(
        self,
        connection: MCPConnection,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enviar request y recibir respuesta"""
        if not connection.process or not connection.process.stdin or not connection.process.stdout:
            return {"error": {"code": -1, "message": "Proceso MCP no disponible"}}
        
        try:
            # Escribir request
            request_str = json.dumps(request) + "\n"
            connection.process.stdin.write(request_str.encode())
            connection.process.stdin.flush()
            
            # Leer response con timeout
            loop = asyncio.get_event_loop()
            
            def read_line():
                return connection.process.stdout.readline()
            
            # Timeout de 30 segundos para operaciones largas
            response_line = await asyncio.wait_for(
                loop.run_in_executor(None, read_line),
                timeout=30.0
            )
            
            if response_line:
                response = json.loads(response_line.decode())
                return response
            else:
                return {"error": {"code": -1, "message": "Sin respuesta del servidor MCP"}}
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout esperando respuesta MCP para {request.get('method')}")
            return {"error": {"code": -1, "message": "Timeout esperando respuesta"}}
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando respuesta MCP: {e}")
            return {"error": {"code": -1, "message": f"Respuesta inválida: {e}"}}
        except Exception as e:
            logger.error(f"Error comunicando con MCP: {e}")
            return {"error": {"code": -1, "message": str(e)}}
    
    async def call_tool(
        self,
        connection_id: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Llamar a una herramienta MCP"""
        connection = self.connections.get(connection_id)
        if not connection:
            return {"error": f"Conexión MCP no encontrada: {connection_id}", "success": False}
        
        if not connection.is_connected:
            # Intentar conectar
            connected = await self.connect(connection_id)
            if not connected:
                return {"error": f"No se pudo conectar a {connection.name}", "success": False}
        
        logger.info(f"Llamando tool MCP: {tool_name}", connection=connection.name, args=arguments)
        
        # Usar HTTP o STDIO según el tipo de conexión
        if connection.conn_type in (MCPConnectionType.HTTP, MCPConnectionType.SSE):
            response = await self._send_request_http(
                connection,
                "tools/call",
                {"name": tool_name, "arguments": arguments}
            )
        else:
            response = await self._send_request(
                connection,
                "tools/call",
                {"name": tool_name, "arguments": arguments}
            )
        
        if response.get("error"):
            return {
                "error": response["error"].get("message", str(response["error"])),
                "success": False
            }
        
        result = response.get("result", {})
        
        # Procesar contenido de la respuesta
        content = result.get("content", [])
        if content:
            # Extraer texto y/o imágenes
            texts = []
            images = []
            for item in content:
                if item.get("type") == "text":
                    texts.append(item.get("text", ""))
                elif item.get("type") == "image":
                    images.append({
                        "data": item.get("data"),
                        "mimeType": item.get("mimeType")
                    })
            
            return {
                "success": True,
                "text": "\n".join(texts) if texts else None,
                "images": images if images else None,
                "raw": content
            }
        
        return {"success": True, "data": result}
    
    async def _send_request_http(
        self,
        connection: MCPConnection,
        method: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enviar request JSON-RPC via HTTP usando cliente persistente"""
        if not connection.server_url:
            return {"error": {"code": -1, "message": "URL del servidor no configurada"}}
        
        # Obtener el cliente persistente
        client = self._http_clients.get(connection.id)
        if not client:
            return {"error": {"code": -1, "message": "Cliente HTTP no inicializado. Reconecte."}}
        
        self._request_id += 1
        base_url = connection.server_url.rstrip('/')
        
        try:
            response = await client.post(
                f"{base_url}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": self._request_id,
                    "method": method,
                    "params": params
                }
            )
            
            if response.status_code == 200:
                return self._parse_sse_response(response.text) or {"error": {"code": -1, "message": "Respuesta vacía"}}
            else:
                return {"error": {"code": response.status_code, "message": response.text}}
                
        except Exception as e:
            logger.error(f"Error en request HTTP MCP: {e}")
            return {"error": {"code": -1, "message": str(e)}}
    
    async def read_resource(
        self,
        connection_id: str,
        uri: str
    ) -> Dict[str, Any]:
        """Leer un recurso MCP"""
        connection = self.connections.get(connection_id)
        if not connection or not connection.is_connected:
            return {"error": "Conexión no disponible", "success": False}
        
        response = await self._send_request(
            connection,
            "resources/read",
            {"uri": uri}
        )
        
        if response.get("error"):
            return {"error": response["error"], "success": False}
        
        return {"success": True, "data": response.get("result", {})}
    
    async def disconnect(self, connection_id: str):
        """Desconectar de un servidor MCP"""
        connection = self.connections.get(connection_id)
        if connection:
            # Cerrar proceso STDIO si existe
            if connection.process:
                try:
                    connection.process.terminate()
                    connection.process.wait(timeout=5)
                except Exception:
                    connection.process.kill()
                connection.process = None
            
            # Cerrar cliente HTTP si existe
            if connection_id in self._http_clients:
                try:
                    await self._http_clients[connection_id].aclose()
                except Exception:
                    pass
                del self._http_clients[connection_id]
            
            connection.is_connected = False
            connection.tools = []
            connection.resources = []
            logger.info(f"Desconectado de MCP: {connection.name}")
    
    async def disconnect_all(self):
        """Desconectar de todos los servidores MCP"""
        for conn_id in list(self.connections.keys()):
            await self.disconnect(conn_id)
    
    def get_connection(self, connection_id: str) -> Optional[MCPConnection]:
        """Obtener una conexión por ID"""
        return self.connections.get(connection_id)
    
    def get_connection_by_name(self, name: str) -> Optional[MCPConnection]:
        """Obtener una conexión por nombre"""
        for conn in self.connections.values():
            if conn.name == name:
                return conn
        return None
    
    def get_tools(self, connection_id: str) -> List[MCPTool]:
        """Obtener herramientas de una conexión"""
        connection = self.connections.get(connection_id)
        return connection.tools if connection else []
    
    def get_all_tools(self) -> Dict[str, List[MCPTool]]:
        """Obtener todas las herramientas de todas las conexiones"""
        return {
            conn_id: conn.tools
            for conn_id, conn in self.connections.items()
            if conn.is_connected
        }
    
    def list_connections(self) -> List[Dict[str, Any]]:
        """Listar todas las conexiones"""
        return [
            {
                "id": conn.id,
                "name": conn.name,
                "type": conn.conn_type.value,
                "description": conn.description,
                "is_connected": conn.is_connected,
                "tools_count": len(conn.tools),
                "resources_count": len(conn.resources),
                "server_info": conn.server_info
            }
            for conn in self.connections.values()
        ]
    
    async def register_connection(self, connection: MCPConnection) -> str:
        """Registrar una nueva conexión (sin persistir en Strapi)"""
        self.connections[connection.id] = connection
        self._locks[connection.id] = asyncio.Lock()
        return connection.id
    
    async def ensure_playwright_connection(self) -> Optional[MCPConnection]:
        """
        Asegura que existe una conexión de Playwright.
        Si no existe en Strapi, crea una conexión temporal apuntando al servicio Docker.
        """
        # Buscar conexión existente
        conn = self.get_connection_by_name("playwright-browser")
        if conn:
            return conn
        
        # Crear conexión temporal para el servicio Docker
        playwright_url = MCP_PLAYWRIGHT_URL
        
        conn = MCPConnection(
            id=str(uuid.uuid4()),
            name="playwright-browser",
            conn_type=MCPConnectionType.HTTP,
            description="Navegador Chrome controlado por Playwright (auto-configurado)",
            server_url=playwright_url
        )
        
        await self.register_connection(conn)
        logger.info(f"Conexión Playwright auto-registrada: {playwright_url}")
        
        return conn


# Instancia global del cliente MCP
mcp_client = MCPClient()
