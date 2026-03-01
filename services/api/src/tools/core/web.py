"""
Brain 2.0 Core Tools - Web (2 tools)

- web_search: Buscar información en internet
- web_fetch: Obtener contenido de una URL

Proveedores de búsqueda soportados:
- openai: Búsqueda nativa de OpenAI (usa Bing, mejor integración)
- duckduckgo: Gratis, sin API key, pero con rate limiting
- serper: API de Google, 2500 queries/mes gratis
- tavily: API optimizada para AI, 1000 queries/mes gratis
"""

import time
from typing import Dict, Any, Optional, List
import structlog

logger = structlog.get_logger()

# Importar configuración
try:
    from ..config import get_web_config
except ImportError:
    get_web_config = None


# ============================================
# Tool Handlers
# ============================================

async def web_search(
    query: str,
    max_results: int = 5
) -> Dict[str, Any]:
    """
    Busca información en internet.
    
    Soporta múltiples proveedores configurables:
    - duckduckgo: Gratis, sin API key
    - serper: Google Search API (2500/mes gratis)
    - tavily: Optimizado para AI (1000/mes gratis)
    
    Args:
        query: Consulta de búsqueda
        max_results: Número máximo de resultados (default: 5)
    
    Returns:
        {"success": True, "results": [...]} o {"error": str}
    """
    # Obtener configuración
    config = get_web_config() if get_web_config else None
    provider = config.search_provider if config else "duckduckgo"
    api_key = config.search_api_key if config else None
    
    if config and not config.search_enabled:
        return {
            "success": False,
            "error": "Web search is disabled in configuration"
        }
    
    # Obtener API key de OpenAI desde Strapi
    openai_api_key = await _get_openai_api_key()
    
    logger.info(f"🔎 web_search: {query}", provider=provider, max_results=max_results)
    
    # Seleccionar proveedor
    # Reject Brain API keys that were leaked into OPENAI_API_KEY
    if openai_api_key and openai_api_key.startswith("sk-brain"):
        openai_api_key = None

    if provider == "openai" and openai_api_key:
        result = await _search_openai(query, max_results, openai_api_key)
        if result.get("success"):
            return result
        logger.warning("OpenAI search failed, falling back to DuckDuckGo")
        return await _search_duckduckgo(query, max_results)
    elif provider == "serper" and api_key:
        return await _search_serper(query, max_results, api_key)
    elif provider == "tavily" and api_key:
        return await _search_tavily(query, max_results, api_key)
    elif openai_api_key:
        result = await _search_openai(query, max_results, openai_api_key)
        if result.get("success"):
            return result
        logger.warning("OpenAI search failed, falling back to DuckDuckGo")
        return await _search_duckduckgo(query, max_results)
    else:
        return await _search_duckduckgo(query, max_results)


async def _get_openai_api_key() -> Optional[str]:
    """Obtiene la API key de OpenAI desde Strapi o variables de entorno"""
    import os
    
    # Primero intentar desde Strapi
    try:
        from ...providers.llm_provider import get_provider_by_type
        
        openai_provider = await get_provider_by_type("openai")
        if openai_provider and openai_provider.api_key:
            logger.debug("OpenAI API key loaded from Strapi")
            return openai_provider.api_key
    except Exception as e:
        logger.warning(f"Could not load OpenAI provider from Strapi: {e}")
    
    # Fallback a variable de entorno
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        logger.debug("OpenAI API key loaded from environment")
        return env_key
    
    return None


async def _search_openai(query: str, max_results: int, api_key: str) -> Dict[str, Any]:
    """
    Búsqueda con OpenAI Native Web Search (usa Bing).
    
    Usa Chat Completions API con modelos search-preview que tienen
    búsqueda web integrada (sin necesidad de tools).
    
    Modelos disponibles:
    - gpt-4o-mini-search-preview (más barato)
    - gpt-4o-search-preview (más capaz)
    
    Ventajas:
    - Sin rate limiting
    - Mejor integración con LLM
    - Resultados actualizados y citados
    """
    try:
        import httpx
        
        # Usar modelo mini para búsquedas (más económico)
        # Estos modelos tienen web search integrado, no necesitan tools
        model = "gpt-4o-mini-search-preview"
        
        # Prompt optimizado para obtener resultados estructurados
        search_prompt = f"""Search the web for: {query}

Provide {max_results} relevant results with:
1. Title
2. URL
3. Brief description (1-2 sentences)

Format each result clearly. Be factual and cite sources."""

        # Chat Completions - los modelos *-search-preview no necesitan tools
        # Nota: estos modelos no soportan temperature
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": search_prompt}],
            "max_tokens": 1500
        }
        
        logger.info(f"🔎 OpenAI search starting", model=model, query=query[:50])
        
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
                error_msg = error_data.get("error", {}).get("message", str(error_data)) if isinstance(error_data, dict) else str(error_data)
                logger.error(f"OpenAI API error: {response.status_code}", error=error_msg)
                return {
                    "success": False,
                    "error": f"OpenAI API error: {error_msg}",
                    "query": query,
                    "provider": "openai"
                }
            
            data = response.json()
            
            # Extraer contenido de la respuesta
            content = ""
            if data.get("choices"):
                message = data["choices"][0].get("message", {})
                content = message.get("content", "")
            
            # Parsear resultados
            results_list = _parse_openai_search_results(content, max_results)
            
            logger.info(
                f"✅ OpenAI web search completed",
                query=query,
                results_count=len(results_list),
                model=model
            )
            
            return {
                "success": True,
                "query": query,
                "provider": "openai",
                "model": model,
                "results": results_list,
                "count": len(results_list),
                "raw_content": content
            }
            
    except Exception as e:
        logger.error(f"OpenAI search error: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "provider": "openai"
        }


def _parse_openai_search_results(content: str, max_results: int) -> List[Dict[str, str]]:
    """
    Parsea los resultados de búsqueda de OpenAI.
    
    Maneja el formato markdown típico de OpenAI:
    **1. Title**
    - **URL:** ([domain](full_url))
    - **Description:** text
    """
    import re
    
    results = []
    
    # Dividir por secciones numeradas (**1., **2., etc)
    sections = re.split(r'\*\*\d+\.', content)
    
    for section in sections[1:]:  # Skip primera sección vacía
        if not section.strip():
            continue
        
        # Extraer título (primera línea después del número)
        title_match = re.search(r'^([^*\n]+)', section.strip())
        title = title_match.group(1).strip().rstrip('*') if title_match else ""
        
        # Extraer URL - buscar formato markdown [text](url)
        url_match = re.search(r'\[([^\]]+)\]\(([^)]+)\)', section)
        if url_match:
            url = url_match.group(2).rstrip(')')  # Limpiar paréntesis extra
            # Limpiar parámetros de tracking si es necesario
            url = re.sub(r'\?utm_source=openai$', '', url)
        else:
            # Fallback a URL directa
            url_direct = re.search(r'https?://[^\s\)]+', section)
            url = url_direct.group(0).rstrip(')') if url_direct else ""
        
        # Extraer descripción
        desc_match = re.search(r'\*\*Description:\*\*\s*([^\n]+)', section)
        if desc_match:
            snippet = desc_match.group(1).strip()
        else:
            # Fallback: tomar texto después del URL hasta el final o próxima línea
            snippet_parts = re.findall(r'(?:Description|Brief)[:\s]*([^\n*]+)', section, re.IGNORECASE)
            snippet = snippet_parts[0].strip() if snippet_parts else ""
        
        if title or url:
            results.append({
                "position": len(results) + 1,
                "title": title.strip('* '),
                "snippet": snippet,
                "url": url
            })
        
        if len(results) >= max_results:
            break
    
    # Si no se encontraron resultados con el formato estructurado,
    # intentar extraer URLs directamente del contenido
    if not results:
        urls = re.findall(r'\[([^\]]+)\]\((https?://[^)]+)\)', content)
        for idx, (text, url) in enumerate(urls[:max_results]):
            results.append({
                "position": idx + 1,
                "title": text,
                "snippet": "",
                "url": url.rstrip(')')
            })
    
    return results


async def _search_duckduckgo(query: str, max_results: int) -> Dict[str, Any]:
    """Búsqueda con DuckDuckGo (gratis, con rate limiting)"""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return {
            "success": False,
            "error": "duckduckgo-search not installed",
            "query": query
        }
    
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            results_list = []
            with DDGS() as ddgs:
                search_results = ddgs.text(
                    query, 
                    max_results=max_results,
                    region='wt-wt',
                    safesearch='moderate'
                )
                
                for idx, result in enumerate(search_results):
                    results_list.append({
                        "position": idx + 1,
                        "title": result.get("title", ""),
                        "snippet": result.get("body", ""),
                        "url": result.get("href", ""),
                    })
            
            return {
                "success": True,
                "query": query,
                "provider": "duckduckgo",
                "results": results_list,
                "count": len(results_list)
            }
            
        except Exception as e:
            if "ratelimit" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "provider": "duckduckgo",
                "hint": "DuckDuckGo rate limited. Configure an API-based provider like Serper or Tavily."
            }
    
    return {"success": False, "error": "Max retries exceeded", "query": query}


async def _search_serper(query: str, max_results: int, api_key: str) -> Dict[str, Any]:
    """Búsqueda con Serper.dev (Google Search API)"""
    try:
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "q": query,
                    "num": max_results
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            results_list = []
            for idx, item in enumerate(data.get("organic", [])[:max_results]):
                results_list.append({
                    "position": idx + 1,
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "url": item.get("link", ""),
                })
            
            return {
                "success": True,
                "query": query,
                "provider": "serper",
                "results": results_list,
                "count": len(results_list)
            }
            
    except Exception as e:
        logger.error(f"Serper search error: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "provider": "serper"
        }


async def _search_tavily(query: str, max_results: int, api_key: str) -> Dict[str, Any]:
    """Búsqueda con Tavily (optimizado para AI)"""
    try:
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                headers={"Content-Type": "application/json"},
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": max_results,
                    "include_answer": False,
                    "include_raw_content": False
                }
            )
            
            response.raise_for_status()
            data = response.json()
            
            results_list = []
            for idx, item in enumerate(data.get("results", [])[:max_results]):
                results_list.append({
                    "position": idx + 1,
                    "title": item.get("title", ""),
                    "snippet": item.get("content", ""),
                    "url": item.get("url", ""),
                })
            
            return {
                "success": True,
                "query": query,
                "provider": "tavily",
                "results": results_list,
                "count": len(results_list)
            }
            
    except Exception as e:
        logger.error(f"Tavily search error: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query,
            "provider": "tavily"
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
