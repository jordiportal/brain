"""
Tool Registry - Registro central de herramientas para agentes
"""

import structlog
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum

from .openapi_tools import OpenAPITool, openapi_toolkit

logger = structlog.get_logger()


class ToolType(str, Enum):
    """Tipos de herramientas disponibles"""
    OPENAPI = "openapi"
    MCP = "mcp"
    BUILTIN = "builtin"
    CUSTOM = "custom"


@dataclass
class ToolDefinition:
    """Definición de una herramienta"""
    id: str
    name: str
    description: str
    type: ToolType
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Para tools builtin/custom
    handler: Optional[Callable] = None
    
    # Para tools OpenAPI
    openapi_tool: Optional[OpenAPITool] = None
    
    # Para tools MCP
    mcp_server: Optional[str] = None
    mcp_tool_name: Optional[str] = None
    
    def to_function_schema(self) -> Dict[str, Any]:
        """Convierte a schema de función para el LLM"""
        if self.openapi_tool:
            return self.openapi_tool.to_function_schema()
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class ToolRegistry:
    """Registro central de todas las herramientas"""
    
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self._builtin_registered = False
    
    def register(self, tool: ToolDefinition) -> None:
        """Registra una herramienta"""
        self.tools[tool.id] = tool
        logger.debug(f"Tool registrada: {tool.id} ({tool.type})")
    
    def register_builtin(
        self,
        id: str,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable
    ) -> None:
        """Registra una herramienta builtin"""
        tool = ToolDefinition(
            id=id,
            name=name,
            description=description,
            type=ToolType.BUILTIN,
            parameters=parameters,
            handler=handler
        )
        self.register(tool)
    
    def register_openapi_tool(self, openapi_tool: OpenAPITool) -> None:
        """Registra una herramienta OpenAPI"""
        tool = ToolDefinition(
            id=openapi_tool.id,
            name=openapi_tool.name,
            description=openapi_tool.description,
            type=ToolType.OPENAPI,
            openapi_tool=openapi_tool
        )
        self.register(tool)
    
    async def load_openapi_tools(self) -> int:
        """Carga todas las herramientas OpenAPI"""
        tools = await openapi_toolkit.load_all_tools()
        
        for tool in tools.values():
            self.register_openapi_tool(tool)
        
        return len(tools)
    
    def get(self, tool_id: str) -> Optional[ToolDefinition]:
        """Obtiene una herramienta por ID"""
        return self.tools.get(tool_id)
    
    def list(self, tool_type: Optional[ToolType] = None) -> List[ToolDefinition]:
        """Lista herramientas, opcionalmente filtradas por tipo"""
        if tool_type:
            return [t for t in self.tools.values() if t.type == tool_type]
        return list(self.tools.values())
    
    def get_tools_for_llm(self, tool_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Obtiene las herramientas en formato para el LLM"""
        if tool_ids:
            tools = [self.tools[tid] for tid in tool_ids if tid in self.tools]
        else:
            tools = list(self.tools.values())
        
        return [tool.to_function_schema() for tool in tools]
    
    async def execute(self, tool_id: str, **kwargs) -> Dict[str, Any]:
        """Ejecuta una herramienta"""
        tool = self.get(tool_id)
        if not tool:
            return {"error": f"Herramienta no encontrada: {tool_id}"}
        
        try:
            if tool.type == ToolType.OPENAPI and tool.openapi_tool:
                return await tool.openapi_tool.execute(**kwargs)
            
            elif tool.type == ToolType.BUILTIN and tool.handler:
                result = tool.handler(**kwargs)
                # Si es async, await
                if hasattr(result, '__await__'):
                    result = await result
                return {"success": True, "data": result}
            
            elif tool.type == ToolType.MCP:
                # TODO: Implementar ejecución MCP
                return {"error": "MCP tools no implementado aún"}
            
            else:
                return {"error": f"No se puede ejecutar tool de tipo {tool.type}"}
                
        except Exception as e:
            logger.error(f"Error ejecutando tool {tool_id}: {e}")
            return {"error": str(e), "success": False}
    
    def register_builtin_tools(self) -> None:
        """Registra las herramientas builtin por defecto"""
        if self._builtin_registered:
            return
        
        # Calculator
        self.register_builtin(
            id="calculator",
            name="calculator",
            description="Realiza cálculos matemáticos. Soporta operaciones básicas (+, -, *, /) y funciones como sqrt, pow, sin, cos.",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Expresión matemática a evaluar, ej: '2 + 2', 'sqrt(16)', 'pow(2, 8)'"
                    }
                },
                "required": ["expression"]
            },
            handler=self._builtin_calculator
        )
        
        # Current DateTime
        self.register_builtin(
            id="current_datetime",
            name="current_datetime",
            description="Obtiene la fecha y hora actual del sistema.",
            parameters={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "description": "Formato de fecha (opcional). Por defecto ISO 8601."
                    }
                },
                "required": []
            },
            handler=self._builtin_datetime
        )
        
        # Web Search
        self.register_builtin(
            id="web_search",
            name="web_search",
            description="Busca información en la web usando DuckDuckGo. Útil para obtener información actualizada, noticias, datos, etc.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Consulta de búsqueda. Ej: 'clima en Madrid', 'últimas noticias Python', 'precio Bitcoin'"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Número máximo de resultados (por defecto 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            },
            handler=self._builtin_web_search
        )
        
        # Nano Banana (Google Gemini Image Generation)
        # Nota: El handler se define como método async más abajo
        nano_banana_tool = ToolDefinition(
            id="nano_banana",
            name="nano_banana",
            description="Genera imágenes usando Google Gemini (Nano Banana). Crea imágenes realistas, artísticas, o ilustraciones basadas en descripciones de texto. Soporta hasta 1024px de resolución.",
            type=ToolType.BUILTIN,
            parameters={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Descripción detallada de la imagen a generar. Ej: 'un gato astronauta flotando en el espacio', 'paisaje montañoso al atardecer', 'logo minimalista para una empresa de tecnología'"
                    },
                    "model": {
                        "type": "string",
                        "description": "Modelo a usar: 'gemini-2.5-flash-image' (rápido, 1024px) o 'gemini-3-pro-image-preview' (alta calidad, 4K). Por defecto gemini-2.5-flash-image",
                        "default": "gemini-2.5-flash-image",
                        "enum": ["gemini-2.5-flash-image", "gemini-3-pro-image-preview"]
                    }
                },
                "required": ["prompt"]
            },
            handler=lambda **kwargs: self._builtin_nano_banana(**kwargs)
        )
        self.register(nano_banana_tool)
        
        self._builtin_registered = True
        logger.info("Tools builtin registradas")
    
    def _builtin_calculator(self, expression: str) -> Dict[str, Any]:
        """Calculadora básica"""
        import math
        
        # Funciones permitidas
        allowed = {
            'sqrt': math.sqrt,
            'pow': pow,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'log': math.log,
            'log10': math.log10,
            'abs': abs,
            'round': round,
            'pi': math.pi,
            'e': math.e
        }
        
        try:
            # Evaluar expresión de forma segura
            result = eval(expression, {"__builtins__": {}}, allowed)
            return {"result": result, "expression": expression}
        except Exception as e:
            return {"error": str(e), "expression": expression}
    
    def _builtin_datetime(self, format: str = None) -> Dict[str, Any]:
        """Obtiene fecha/hora actual"""
        from datetime import datetime
        
        now = datetime.now()
        
        if format:
            try:
                formatted = now.strftime(format)
                return {"datetime": formatted, "format": format}
            except:
                pass
        
        return {
            "datetime": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timestamp": now.timestamp()
        }
    
    def _builtin_web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Búsqueda web con DuckDuckGo"""
        import time
        
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            logger.error("duckduckgo-search no está instalado")
            return {
                "error": "duckduckgo-search no está instalado. Ejecuta: pip install duckduckgo-search",
                "query": query
            }
        
        # Intentar hasta 3 veces con delay incremental
        max_retries = 3
        retry_delay = 1  # segundos
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Buscando en web: {query}", max_results=max_results, attempt=attempt + 1)
                
                results_list = []
                with DDGS() as ddgs:
                    # Búsqueda de texto con timeout
                    search_results = ddgs.text(
                        query, 
                        max_results=max_results,
                        region='wt-wt',  # World region
                        safesearch='moderate',
                        timelimit=None
                    )
                    
                    for idx, result in enumerate(search_results):
                        results_list.append({
                            "position": idx + 1,
                            "title": result.get("title", ""),
                            "snippet": result.get("body", ""),
                            "url": result.get("href", ""),
                        })
                
                logger.info(f"Búsqueda completada: {len(results_list)} resultados", query=query)
                
                return {
                    "success": True,
                    "query": query,
                    "results": results_list,
                    "count": len(results_list)
                }
                
            except Exception as e:
                error_msg = str(e)
                
                # Si es rate limit y no es el último intento, esperar y reintentar
                if "ratelimit" in error_msg.lower() and attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    logger.warning(
                        f"Rate limit detectado, esperando {wait_time}s antes de reintentar",
                        query=query,
                        attempt=attempt + 1
                    )
                    time.sleep(wait_time)
                    continue
                
                # Si llegamos aquí, es el último intento o un error diferente
                logger.error(f"Error en búsqueda web: {e}", query=query, attempt=attempt + 1)
                return {
                    "error": str(e),
                    "query": query,
                    "success": False,
                    "hint": "DuckDuckGo puede tener rate limiting temporal. Intenta de nuevo en 30 segundos."
                }
    
    async def _builtin_nano_banana(self, prompt: str, model: str = "gemini-2.5-flash-image") -> Dict[str, Any]:
        """
        Genera imágenes con Google Nano Banana (Gemini Image).
        
        Devuelve la imagen en base64 para que el agente pueda mostrarla.
        """
        import httpx
        import base64
        import os
        
        # Obtener API key desde el provider Gemini en BD
        try:
            from src.providers.llm_provider import get_provider_by_type
            provider = await get_provider_by_type("gemini")
            if not provider or not provider.api_key:
                return {
                    "error": "No se encontró configuración de Google Gemini con API key",
                    "hint": "Configura un provider Gemini activo con API key en Strapi"
                }
            api_key = provider.api_key
            base_url = provider.base_url
        except Exception as e:
            logger.error(f"Error obteniendo provider Gemini: {e}")
            return {
                "error": f"Error obteniendo configuración: {str(e)}"
            }
        
        try:
            logger.info(f"Generando imagen con Nano Banana: {prompt[:100]}", model=model)
            
            # Endpoint de Gemini para generación de imágenes
            url = f"{base_url}/models/{model}:generateContent?key={api_key}"
            
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": f"Generate an image: {prompt}"
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 1.0,
                    "topK": 40,
                    "topP": 0.95,
                }
            }
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json=payload
                )
                
                if response.status_code != 200:
                    logger.error(f"Error Gemini API: {response.text}")
                    return {
                        "error": f"Error API: {response.status_code}",
                        "details": response.text[:500]
                    }
                
                data = response.json()
                
                # Extraer la imagen generada
                candidates = data.get("candidates", [])
                if not candidates:
                    return {
                        "error": "No se generó ninguna imagen",
                        "response": data
                    }
                
                content_parts = candidates[0].get("content", {}).get("parts", [])
                
                # Buscar la parte que contiene la imagen
                image_data = None
                for part in content_parts:
                    if "inlineData" in part:
                        image_data = part["inlineData"]["data"]
                        mime_type = part["inlineData"]["mimeType"]
                        break
                
                if not image_data:
                    return {
                        "error": "No se encontró imagen en la respuesta",
                        "response_preview": str(data)[:500]
                    }
                
                logger.info(f"Imagen generada exitosamente", size=len(image_data), mime=mime_type)
                
                return {
                    "success": True,
                    "prompt": prompt,
                    "model": model,
                    "image_base64": image_data,
                    "mime_type": mime_type,
                    "markdown": f"![{prompt}](data:{mime_type};base64,{image_data})",
                    "info": f"Imagen generada con {model}. Tamaño: ~{len(image_data) // 1024}KB"
                }
                
        except Exception as e:
            logger.error(f"Error generando imagen: {e}")
            return {
                "error": str(e),
                "prompt": prompt,
                "success": False
            }


# Instancia global
tool_registry = ToolRegistry()
