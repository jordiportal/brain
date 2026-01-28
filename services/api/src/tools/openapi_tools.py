"""
OpenAPI Tools - Convierte especificaciones OpenAPI en herramientas para agentes
"""

import re
import json
import httpx
import structlog
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlencode

from ..db.repositories import OpenAPIConnectionRepository

logger = structlog.get_logger()


@dataclass
class OpenAPITool:
    """Representa una herramienta generada desde un endpoint OpenAPI"""
    id: str
    name: str
    description: str
    method: str
    path: str
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[str, Any] = field(default_factory=dict)
    
    # Conexión
    connection_id: str = ""
    base_url: str = ""
    auth_type: str = "none"
    auth_token: Optional[str] = None
    auth_header: str = "Authorization"
    auth_prefix: str = "Bearer"
    custom_headers: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30000
    
    def to_function_schema(self) -> Dict[str, Any]:
        """Convierte a schema de función para el LLM"""
        properties = {}
        required = []
        
        # Parámetros de path y query
        for param in self.parameters:
            param_name = param.get("name", "")
            param_schema = param.get("schema", {"type": "string"})
            
            param_def = {
                "type": param_schema.get("type", "string"),
                "description": param.get("description", f"Parameter {param_name}")
            }
            
            # Si es array, incluir items
            if param_schema.get("type") == "array":
                param_def["items"] = param_schema.get("items", {"type": "string"})
            
            # Si tiene enum, incluirlo
            if "enum" in param_schema:
                param_def["enum"] = param_schema["enum"]
            
            properties[param_name] = param_def
            
            if param.get("required", False):
                required.append(param_name)
        
        # Request body
        if self.request_body:
            content = self.request_body.get("content", {})
            json_schema = content.get("application/json", {}).get("schema", {})
            
            if json_schema.get("properties"):
                for prop_name, prop_schema in json_schema["properties"].items():
                    # Copiar schema completo para preservar arrays, enums, etc.
                    param_def = {
                        "type": prop_schema.get("type", "string"),
                        "description": prop_schema.get("description", f"Body parameter {prop_name}")
                    }
                    
                    # Si es array, incluir items (requerido por OpenAI)
                    if prop_schema.get("type") == "array":
                        param_def["items"] = prop_schema.get("items", {"type": "string"})
                    
                    # Si tiene enum, incluirlo
                    if "enum" in prop_schema:
                        param_def["enum"] = prop_schema["enum"]
                    
                    properties[prop_name] = param_def
                
                if json_schema.get("required"):
                    required.extend(json_schema["required"])
        
        # Truncar el nombre si es muy largo (OpenAI límite: 64 chars)
        function_name = self.name
        if len(function_name) > 64:
            # Truncar pero mantener el final que suele ser más descriptivo
            function_name = function_name[:60] + "_" + str(hash(function_name) % 1000)
        
        return {
            "name": function_name,
            "description": self.description + (f" (ID original: {self.name})" if function_name != self.name else ""),
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": list(set(required))
            }
        }
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Ejecuta la llamada al endpoint"""
        try:
            # Construir URL con path parameters
            url = self.path
            path_params = {}
            query_params = {}
            body_params = {}
            
            for param in self.parameters:
                param_name = param.get("name", "")
                param_in = param.get("in", "query")
                
                if param_name in kwargs:
                    if param_in == "path":
                        path_params[param_name] = kwargs[param_name]
                    elif param_in == "query":
                        query_params[param_name] = kwargs[param_name]
            
            # Reemplazar path parameters
            for name, value in path_params.items():
                url = url.replace(f"{{{name}}}", str(value))
            
            # Body parameters (lo que no es path ni query)
            if self.request_body:
                for key, value in kwargs.items():
                    if key not in path_params and key not in query_params:
                        body_params[key] = value
            
            # Construir URL completa
            full_url = urljoin(self.base_url, url)
            if query_params:
                full_url += "?" + urlencode(query_params)
            
            # Headers
            headers = dict(self.custom_headers)
            headers["Content-Type"] = "application/json"
            
            # Auth
            if self.auth_type == "bearer" and self.auth_token:
                headers[self.auth_header] = f"{self.auth_prefix} {self.auth_token}"
            elif self.auth_type == "apikey" and self.auth_token:
                headers[self.auth_header] = self.auth_token
            
            # Ejecutar request
            timeout = httpx.Timeout(self.timeout / 1000)
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                if self.method.upper() == "GET":
                    response = await client.get(full_url, headers=headers)
                elif self.method.upper() == "POST":
                    response = await client.post(full_url, headers=headers, json=body_params or None)
                elif self.method.upper() == "PUT":
                    response = await client.put(full_url, headers=headers, json=body_params or None)
                elif self.method.upper() == "PATCH":
                    response = await client.patch(full_url, headers=headers, json=body_params or None)
                elif self.method.upper() == "DELETE":
                    response = await client.delete(full_url, headers=headers)
                else:
                    return {"error": f"Método HTTP no soportado: {self.method}"}
                
                # Parsear respuesta
                try:
                    result = response.json()
                except:
                    result = {"text": response.text}
                
                return {
                    "success": response.is_success,
                    "status_code": response.status_code,
                    "data": result
                }
                
        except httpx.TimeoutException:
            return {"error": "Timeout en la llamada al servicio", "success": False}
        except Exception as e:
            logger.error(f"Error ejecutando OpenAPI tool: {e}")
            return {"error": str(e), "success": False}


class OpenAPIToolkit:
    """Gestiona las conexiones OpenAPI y genera herramientas"""
    
    def __init__(self):
        self.connections: Dict[str, Dict] = {}
        self.tools: Dict[str, OpenAPITool] = {}
        self._loaded = False
    
    async def load_connections_from_db(self) -> int:
        """Carga conexiones activas desde PostgreSQL"""
        try:
            db_connections = await OpenAPIConnectionRepository.get_all(active_only=True)
            count = 0
            
            for conn in db_connections:
                conn_id = conn.document_id or str(conn.id)
                self.connections[conn_id] = {
                    "id": conn_id,
                    "name": conn.name,
                    "slug": conn.slug,
                    "specUrl": conn.spec_url,
                    "baseUrl": conn.base_url,
                    "authType": conn.auth_type or "none",
                    "authToken": conn.auth_token,
                    "authHeader": conn.auth_header or "Authorization",
                    "authPrefix": conn.auth_prefix or "Bearer",
                    "timeout": conn.timeout or 30000,
                    "customHeaders": conn.custom_headers or {},
                    "enabledEndpoints": conn.enabled_endpoints,
                    "cachedSpec": conn.cached_spec
                }
                count += 1
                logger.info(f"Conexión cargada: {conn.name} ({conn_id})")
            
            self._loaded = True
            logger.info(f"Cargadas {count} conexiones OpenAPI desde BD")
            return count
                    
        except Exception as e:
            logger.error(f"Error cargando conexiones OpenAPI: {e}")
            return 0
    
    # Alias para compatibilidad
    async def load_connections_from_strapi(self) -> int:
        """Alias para compatibilidad - usa load_connections_from_db"""
        return await self.load_connections_from_db()
    
    async def refresh_connections(self) -> int:
        """Recarga las conexiones desde la BD"""
        self.connections = {}
        self.tools = {}
        self._loaded = False
        return await self.load_connections_from_db()
    
    async def fetch_and_parse_spec(self, connection_id: str) -> Dict[str, Any]:
        """Descarga y parsea la especificación OpenAPI"""
        if connection_id not in self.connections:
            raise ValueError(f"Conexión no encontrada: {connection_id}")
        
        conn = self.connections[connection_id]
        
        # Usar spec cacheada si existe
        if conn.get("cachedSpec"):
            return conn["cachedSpec"]
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(conn["specUrl"])
                
                if response.status_code == 200:
                    spec = response.json()
                    conn["cachedSpec"] = spec
                    return spec
                else:
                    raise Exception(f"Error descargando spec: {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Error obteniendo spec OpenAPI: {e}")
            raise
    
    async def generate_tools(self, connection_id: str) -> List[OpenAPITool]:
        """Genera herramientas a partir de la especificación OpenAPI"""
        spec = await self.fetch_and_parse_spec(connection_id)
        conn = self.connections[connection_id]
        
        tools = []
        enabled_endpoints = conn.get("enabledEndpoints")
        
        # Iterar sobre los paths
        for path, methods in spec.get("paths", {}).items():
            for method, details in methods.items():
                if method not in ["get", "post", "put", "patch", "delete"]:
                    continue
                
                # Generar ID único para la tool
                operation_id = details.get("operationId")
                if not operation_id:
                    # Generar operation_id desde path y method
                    clean_path = re.sub(r'[{}]', '', path).replace('/', '_').strip('_')
                    operation_id = f"{method}_{clean_path}"
                
                # Usar slug o generar desde nombre
                conn_prefix = conn.get('slug') or conn['name'].lower().replace(' ', '_').replace('-', '_')
                tool_id = f"{conn_prefix}_{operation_id}"
                
                # Verificar si está habilitado
                if enabled_endpoints and tool_id not in enabled_endpoints:
                    continue
                
                # Crear herramienta
                tool = OpenAPITool(
                    id=tool_id,
                    name=tool_id,
                    description=details.get("summary") or details.get("description") or f"{method.upper()} {path}",
                    method=method.upper(),
                    path=path,
                    parameters=details.get("parameters", []),
                    request_body=details.get("requestBody"),
                    responses=details.get("responses", {}),
                    connection_id=connection_id,
                    base_url=conn["baseUrl"],
                    auth_type=conn["authType"],
                    auth_token=conn["authToken"],
                    auth_header=conn["authHeader"],
                    auth_prefix=conn["authPrefix"],
                    custom_headers=conn.get("customHeaders", {}),
                    timeout=conn.get("timeout", 30000)
                )
                
                tools.append(tool)
                self.tools[tool_id] = tool
        
        logger.info(f"Generadas {len(tools)} herramientas para {conn['name']}")
        return tools
    
    async def load_all_tools(self) -> Dict[str, OpenAPITool]:
        """Carga todas las herramientas de todas las conexiones"""
        if not self.connections:
            await self.load_connections_from_db()
        
        for conn_id in self.connections:
            try:
                await self.generate_tools(conn_id)
            except Exception as e:
                logger.error(f"Error generando tools para {conn_id}: {e}")
        
        return self.tools
    
    def get_tool(self, tool_id: str) -> Optional[OpenAPITool]:
        """Obtiene una herramienta por ID"""
        return self.tools.get(tool_id)
    
    def list_tools(self, connection_id: Optional[str] = None) -> List[OpenAPITool]:
        """Lista todas las herramientas o las de una conexión específica"""
        if connection_id:
            return [t for t in self.tools.values() if t.connection_id == connection_id]
        return list(self.tools.values())
    
    def get_tools_for_llm(self, connection_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Obtiene las herramientas en formato para el LLM"""
        tools = self.list_tools(connection_id)
        return [tool.to_function_schema() for tool in tools]
    
    async def execute_tool(self, tool_id: str, **kwargs) -> Dict[str, Any]:
        """Ejecuta una herramienta por ID"""
        tool = self.get_tool(tool_id)
        if not tool:
            return {"error": f"Herramienta no encontrada: {tool_id}"}
        
        return await tool.execute(**kwargs)


# Instancia global
openapi_toolkit = OpenAPIToolkit()
