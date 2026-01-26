"""
Brain 2.0 Core Tools - Web (2 tools)

- web_search: Buscar información en internet
- web_fetch: Obtener contenido de una URL
"""

import time
from typing import Dict, Any, Optional, List
import structlog

logger = structlog.get_logger()


# ============================================
# Tool Handlers
# ============================================

async def web_search(
    query: str,
    max_results: int = 5
) -> Dict[str, Any]:
    """
    Busca información en internet usando DuckDuckGo.
    
    Args:
        query: Consulta de búsqueda
        max_results: Número máximo de resultados (default: 5)
    
    Returns:
        {"success": True, "results": [...]} o {"error": str}
    """
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        logger.error("duckduckgo-search no está instalado")
        return {
            "success": False,
            "error": "duckduckgo-search no está instalado. Ejecuta: pip install duckduckgo-search",
            "query": query
        }
    
    # Intentar hasta 3 veces con delay incremental
    max_retries = 3
    retry_delay = 1  # segundos
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🔎 web_search: {query}", max_results=max_results, attempt=attempt + 1)
            
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
            
            logger.info(f"✅ web_search completed: {len(results_list)} resultados", query=query)
            
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
                "success": False,
                "error": str(e),
                "query": query,
                "hint": "DuckDuckGo puede tener rate limiting temporal. Intenta de nuevo en 30 segundos."
            }
    
    return {
        "success": False,
        "error": "Se agotaron los reintentos",
        "query": query
    }


async def web_fetch(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Obtiene el contenido de una URL.
    
    Args:
        url: URL a obtener
        headers: Headers HTTP opcionales
        timeout: Timeout en segundos (default: 30)
    
    Returns:
        {"success": True, "content": str, "status_code": int} o {"error": str}
    """
    try:
        import httpx
    except ImportError:
        logger.error("httpx no está instalado")
        return {
            "success": False,
            "error": "httpx no está instalado. Ejecuta: pip install httpx",
            "url": url
        }
    
    try:
        logger.info(f"🌐 web_fetch: {url}", timeout=timeout)
        
        # Headers por defecto para simular navegador
        default_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        
        if headers:
            default_headers.update(headers)
        
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            verify=True
        ) as client:
            response = await client.get(url, headers=default_headers)
            
            content_type = response.headers.get("content-type", "")
            
            # Para HTML, extraer texto legible
            if "text/html" in content_type:
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Remover scripts y estilos
                    for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                        element.decompose()
                    
                    # Obtener texto
                    text = soup.get_text(separator='\n', strip=True)
                    
                    # Limpiar líneas vacías múltiples
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    content = '\n'.join(lines)
                    
                    # Limitar tamaño
                    if len(content) > 50000:
                        content = content[:50000] + "\n\n... [contenido truncado]"
                    
                except ImportError:
                    # Si no hay BeautifulSoup, devolver HTML raw (limitado)
                    content = response.text[:50000]
                    if len(response.text) > 50000:
                        content += "\n\n... [contenido truncado]"
            
            # Para JSON
            elif "application/json" in content_type:
                try:
                    import json
                    data = response.json()
                    content = json.dumps(data, indent=2, ensure_ascii=False)
                    if len(content) > 50000:
                        content = content[:50000] + "\n\n... [contenido truncado]"
                except Exception:
                    content = response.text[:50000]
            
            # Para texto plano u otros
            else:
                content = response.text[:50000]
                if len(response.text) > 50000:
                    content += "\n\n... [contenido truncado]"
            
            logger.info(
                f"✅ web_fetch completed",
                url=url,
                status=response.status_code,
                content_len=len(content)
            )
            
            return {
                "success": response.status_code < 400,
                "url": str(response.url),
                "status_code": response.status_code,
                "content_type": content_type,
                "content": content,
                "content_length": len(content)
            }
            
    except httpx.TimeoutException:
        logger.warning(f"⏱️ web_fetch timeout: {url}")
        return {
            "success": False,
            "error": f"Timeout después de {timeout} segundos",
            "url": url
        }
    except httpx.RequestError as e:
        logger.error(f"Error en web_fetch: {e}")
        return {
            "success": False,
            "error": f"Error de conexión: {str(e)}",
            "url": url
        }
    except Exception as e:
        logger.error(f"Error en web_fetch: {e}")
        return {
            "success": False,
            "error": str(e),
            "url": url
        }


# ============================================
# Tool Definitions for Registry
# ============================================

WEB_TOOLS = {
    "web_search": {
        "id": "web_search",
        "name": "web_search",
        "description": "Busca información en internet usando DuckDuckGo. Útil para obtener información actualizada, noticias, datos.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Consulta de búsqueda (ej: 'clima Madrid', 'últimas noticias Python', 'precio Bitcoin')"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Número máximo de resultados (default: 5)"
                }
            },
            "required": ["query"]
        },
        "handler": web_search
    },
    "web_fetch": {
        "id": "web_fetch",
        "name": "web_fetch",
        "description": "Obtiene el contenido de una URL. Extrae texto de HTML, soporta JSON y texto plano.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL completa a obtener (ej: 'https://example.com/page')"
                },
                "headers": {
                    "type": "object",
                    "description": "Headers HTTP opcionales"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout en segundos (default: 30)"
                }
            },
            "required": ["url"]
        },
        "handler": web_fetch
    }
}
