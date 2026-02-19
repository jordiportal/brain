"""
SAP BIW Tools - Herramientas directas HTTP contra proxy-biw.

Cada herramienta llama a un endpoint REST del proxy-biw,
leyendo la configuracion de conexion (URL + token) de la tabla
openapi_connections (slug='sap-biw').

No hay mocks ni fallbacks: si el proxy no esta disponible, se
devuelve un error claro para que el LLM informe al usuario.
"""

import time
import httpx
from typing import Dict, Any, List, Optional
from urllib.parse import quote

import structlog

logger = structlog.get_logger()

# Cache de conexion con TTL (5 min) para no consultar BD en cada tool call
_connection_cache: Dict[str, Any] = {}
_CACHE_TTL_SECONDS = 300


def _invalidate_cache():
    """Limpia el cache de conexion (fuerza re-lectura de BD)."""
    _connection_cache.clear()


async def _get_proxy_config() -> Dict[str, str]:
    """
    Obtiene base_url y auth_token de la conexion OpenAPI 'sap-biw' en BD.
    Cachea el resultado en memoria con TTL de 5 minutos.
    
    Returns:
        Dict con 'base_url' y 'token'
    
    Raises:
        ValueError si la conexion no existe o no esta activa
    """
    cached_at = _connection_cache.get("_cached_at", 0)
    if _connection_cache.get("base_url") and (time.time() - cached_at) < _CACHE_TTL_SECONDS:
        return _connection_cache
    
    try:
        from src.db.repositories.openapi_connections import OpenAPIConnectionRepository
        conn = await OpenAPIConnectionRepository.get_by_slug("sap-biw")
        
        if not conn:
            raise ValueError(
                "No existe conexion 'sap-biw' en openapi_connections. "
                "Configure la conexion al proxy BIW en Tools > OpenAPI."
            )
        
        if not conn.is_active:
            raise ValueError(
                "La conexion 'sap-biw' esta desactivada. "
                "Active la conexion en Tools > OpenAPI."
            )
        
        _connection_cache["base_url"] = conn.base_url.rstrip("/")
        _connection_cache["token"] = conn.auth_token or ""
        _connection_cache["_cached_at"] = time.time()
        
        logger.info(
            "SAP BIW proxy config loaded",
            base_url=_connection_cache["base_url"],
            has_token=bool(_connection_cache["token"])
        )
        return _connection_cache
        
    except ImportError:
        raise ValueError("No se puede acceder a la base de datos de configuracion")


async def _proxy_request(
    method: str,
    path: str,
    params: Optional[Dict[str, str]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout: float = 60.0
) -> Dict[str, Any]:
    """
    Realiza una peticion HTTP al proxy-biw.
    
    Args:
        method: GET o POST
        path: Ruta relativa (ej: /api/bi/queries)
        params: Query parameters para GET
        json_body: Body JSON para POST
        timeout: Timeout en segundos
    
    Returns:
        Respuesta JSON del proxy
    """
    config = await _get_proxy_config()
    url = f"{config['base_url']}{path}"
    headers = {}
    if config["token"]:
        headers["Authorization"] = f"Bearer {config['token']}"
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if method.upper() == "GET":
                resp = await client.get(url, headers=headers, params=params)
            else:
                resp = await client.post(url, headers=headers, json=json_body)
            
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return {"data": data, "count": len(data)}
            return data
            
    except httpx.ConnectError:
        return {
            "success": False,
            "error": f"No se puede conectar al proxy BIW en {config['base_url']}. Verifique que el servicio esta corriendo."
        }
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": f"Timeout al conectar con proxy BIW ({timeout}s). La consulta puede ser demasiado grande."
        }
    except httpx.HTTPStatusError as e:
        body = e.response.text[:500] if e.response else ""
        if e.response.status_code == 401:
            _invalidate_cache()
        return {
            "success": False,
            "error": f"Error HTTP {e.response.status_code} del proxy BIW: {body}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error inesperado al llamar proxy BIW: {str(e)}"
        }


# ============================================
# Herramientas BIW
# ============================================

async def bi_list_catalogs() -> Dict[str, Any]:
    """Lista los catalogos (InfoCubes/MultiProviders) disponibles en SAP BIW."""
    logger.info("SAP BIW: listing catalogs")
    result = await _proxy_request("GET", "/api/bi/catalogs")
    if isinstance(result, dict) and "error" not in result:
        result["success"] = True
    return result


async def bi_list_queries(
    catalog: Optional[str] = None,
    filter: Optional[str] = None
) -> Dict[str, Any]:
    """Lista las queries disponibles, opcionalmente filtradas por catalogo o texto."""
    logger.info("SAP BIW: listing queries", catalog=catalog, filter=filter)
    params = {}
    if catalog:
        params["catalog"] = catalog
    if filter:
        params["filter"] = filter
    
    result = await _proxy_request("GET", "/api/bi/queries", params=params)
    if isinstance(result, dict) and "error" not in result:
        result["success"] = True
    return result


async def bi_get_metadata(query_name: str) -> Dict[str, Any]:
    """Obtiene dimensiones y medidas de una query BIW."""
    logger.info("SAP BIW: getting metadata", query=query_name)
    encoded = quote(query_name, safe="")
    result = await _proxy_request("GET", f"/api/bi/queries/{encoded}/metadata")
    if isinstance(result, dict) and "error" not in result:
        result["success"] = True
    return result


async def bi_get_dimension_values(
    query_name: str,
    dimension: str
) -> Dict[str, Any]:
    """Obtiene los valores posibles de una dimension en una query."""
    logger.info("SAP BIW: getting dimension values", query=query_name, dimension=dimension)
    encoded_query = quote(query_name, safe="")
    encoded_dim = quote(dimension, safe="")
    result = await _proxy_request(
        "GET", f"/api/bi/queries/{encoded_query}/dimension-values/{encoded_dim}"
    )
    if isinstance(result, dict) and "error" not in result:
        result["success"] = True
    return result


async def bi_execute_query(
    query: str,
    measures: Optional[List[str]] = None,
    dimension: Optional[str] = None,
    filters: Optional[Dict[str, str]] = None,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Ejecuta una query estructurada contra SAP BIW (genera MDX internamente)."""
    logger.info("SAP BIW: executing query", query=query, dimension=dimension, filters=filters)
    
    body: Dict[str, Any] = {"query": query}
    if measures:
        body["measures"] = measures
    if dimension:
        body["dimension"] = dimension
    if filters:
        body["filters"] = filters
    if options:
        body["options"] = options
    
    result = await _proxy_request("POST", "/api/bi/query", json_body=body, timeout=120.0)
    if isinstance(result, dict) and "error" not in result:
        result["success"] = True
    return result


async def bw_execute_mdx(
    query: str,
    options: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Ejecuta una query MDX directa contra SAP BW."""
    logger.info("SAP BIW: executing MDX", mdx=query[:100])
    
    body: Dict[str, Any] = {"query": query}
    if options:
        body["options"] = options
    
    result = await _proxy_request("POST", "/api/bw/mdx/execute", json_body=body, timeout=120.0)
    if isinstance(result, dict) and "error" not in result:
        result["success"] = True
    return result


# ============================================
# Tool Definitions para el Registry
# ============================================

BIW_TOOLS = {
    "bi_list_catalogs": {
        "id": "bi_list_catalogs",
        "name": "bi_list_catalogs",
        "description": "Lista los catalogos (InfoCubes/MultiProviders) disponibles en SAP BIW. Empieza aqui para descubrir que datos hay disponibles.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "handler": bi_list_catalogs
    },
    "bi_list_queries": {
        "id": "bi_list_queries",
        "name": "bi_list_queries",
        "description": "Lista queries BIW disponibles, filtradas por catalogo o texto. Devuelve nombres de query que puedes usar con bi_get_metadata y bi_execute_query.",
        "parameters": {
            "type": "object",
            "properties": {
                "catalog": {
                    "type": "string",
                    "description": "Filtrar por catalogo (ej: 'ZBOKCOPA'). Opcional."
                },
                "filter": {
                    "type": "string",
                    "description": "Filtro de texto en nombre o descripcion. Opcional."
                }
            },
            "required": []
        },
        "handler": bi_list_queries
    },
    "bi_get_metadata": {
        "id": "bi_get_metadata",
        "name": "bi_get_metadata",
        "description": "Obtiene metadatos completos de una query BIW: dimensiones y medidas con nombres y descripciones. Usa esto para entender que datos contiene una query antes de ejecutarla.",
        "parameters": {
            "type": "object",
            "properties": {
                "query_name": {
                    "type": "string",
                    "description": "Nombre completo de la query incluyendo catalogo (ej: 'ZBOKCOPA/PBI_SEG_CLI_VNE_Q002')"
                }
            },
            "required": ["query_name"]
        },
        "handler": bi_get_metadata
    },
    "bi_get_dimension_values": {
        "id": "bi_get_dimension_values",
        "name": "bi_get_dimension_values",
        "description": "Obtiene los valores posibles de una dimension en una query. Util para descubrir valores validos de filtro (ej: listar segmentos, marcas, grupos de cliente).",
        "parameters": {
            "type": "object",
            "properties": {
                "query_name": {
                    "type": "string",
                    "description": "Nombre completo de la query incluyendo catalogo"
                },
                "dimension": {
                    "type": "string",
                    "description": "Nombre de la dimension (ej: 'ZSEGMEN', '0MATERIAL__YCOPAPH1')"
                }
            },
            "required": ["query_name", "dimension"]
        },
        "handler": bi_get_dimension_values
    },
    "bi_execute_query": {
        "id": "bi_execute_query",
        "name": "bi_execute_query",
        "description": """Ejecuta una query estructurada contra SAP BIW. Especifica la query, medidas, dimension de desglose y filtros. Devuelve datos tabulares limpios. El servicio genera MDX internamente (incluyendo SAP VARIABLES) - nunca necesitas escribir MDX.

IMPORTANTE: Para queries con dimension 0VERSION (como P&L), SIEMPRE filtra "0VERSION": "#" para obtener datos reales. Sin este filtro se suman actual + prevision + objetivo dando totales incorrectos.""",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Nombre completo de la query (ej: 'ZBOKCOPA/PBI_SEG_CLI_VNE_Q002')"
                },
                "measures": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Medidas especificas a devolver (nombres tecnicos). Omitir para todas."
                },
                "dimension": {
                    "type": "string",
                    "description": "Dimension para desglose por filas (ej: 'ZSEGMEN'). Omitir para solo totales."
                },
                "filters": {
                    "type": "object",
                    "description": "Filtros como pares dimension:valor (ej: {\"0CALMONTH\": \"202601\", \"0VERSION\": \"#\"})"
                },
                "options": {
                    "type": "object",
                    "description": "Opciones adicionales (ej: {\"maxRecords\": 10000})"
                }
            },
            "required": ["query"]
        },
        "handler": bi_execute_query
    },
    "bw_execute_mdx": {
        "id": "bw_execute_mdx",
        "name": "bw_execute_mdx",
        "description": "Ejecuta una query MDX directa contra SAP BW. Solo usar cuando bi_execute_query no sea suficiente para consultas muy especificas.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Query MDX completa"
                },
                "options": {
                    "type": "object",
                    "description": "Opciones (ej: {\"maxCells\": 50000, \"cleanup\": true})"
                }
            },
            "required": ["query"]
        },
        "handler": bw_execute_mdx
    }
}
