"""
Native Web Search Tools para OpenAI
Implementa búsqueda web nativa usando la función integrada de OpenAI
"""

import json
from typing import List, Dict, AsyncGenerator, Optional, Any
import httpx
import structlog

logger = structlog.get_logger()


async def call_llm_with_web_search(
    model: str,
    messages: List[Dict],
    api_key: str,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    base_url: str = "https://api.openai.com/v1",
    stream: bool = False
) -> Dict[str, Any]:
    """
    Llamar a OpenAI Responses API con Web Search nativo habilitado.
    
    USA RESPONSES API (no Chat Completions API)
    Docs: https://platform.openai.com/docs/guides/tools-web-search
    
    Args:
        model: Nombre del modelo (debe soportar web search)
        messages: Lista de mensajes [{"role": "user", "content": "..."}]
        api_key: OpenAI API key
        temperature: Temperatura para generación
        max_tokens: Máximo de tokens (opcional)
        base_url: URL base de la API
        stream: Si usar streaming o no
    
    Returns:
        Dict con respuesta y metadatos de búsqueda
    """
    
    # Convertir messages a input (último mensaje del usuario)
    user_message = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_message = msg.get("content", "")
            break
    
    if not user_message:
        user_message = messages[-1].get("content", "") if messages else ""
    
    # IMPORTANTE: Responses API usa /responses, no /chat/completions
    url = f"{base_url}/responses"
    
    # Payload para Responses API
    payload = {
        "model": model,
        "input": user_message,  # Responses API usa "input" no "messages"
        "temperature": temperature,
        "tools": [
            {
                "type": "web_search"  # En Responses API es "web_search" directamente
            }
        ]
    }
    
    if max_tokens:
        payload["max_output_tokens"] = max_tokens  # Nota: es max_output_tokens, no max_tokens
    
    logger.warning(
        "Llamando OpenAI Responses API con web search",
        model=model,
        input_length=len(user_message),
        url=url
    )
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            if response.status_code != 200:
                try:
                    error_data = response.json() if "application/json" in response.headers.get("content-type", "") else response.text
                except:
                    error_data = response.text
                
                error_msg = f"Error OpenAI API: {response.status_code}"
                error_detail = str(error_data)
                
                logger.error(
                    error_msg,
                    status=response.status_code,
                    error_detail=error_detail[:500],
                    model=model,
                    base_url=base_url
                )
                
                # Mostrar error completo en consola para debugging
                print(f"\n{'='*80}")
                print(f"ERROR OpenAI API {response.status_code}")
                print(f"Model: {model}")
                print(f"Base URL: {base_url}")
                print(f"Error Detail: {error_detail}")
                print(f"{'='*80}\n")
                
                raise Exception(f"{error_msg} - {error_detail}")
            
            data = response.json()
            
            # Extraer respuesta del Responses API
            # Formato: {"id": "...", "status": "completed", "output": {...}}
            status = data.get("status")
            output = data.get("output", {})
            
            # El contenido viene en output
            content = ""
            if isinstance(output, dict):
                content = output.get("content", str(output))
            else:
                content = str(output)
            
            logger.warning(
                "Web search completado",
                model=model,
                status=status,
                response_id=data.get("id")
            )
            
            return {
                "success": True,
                "content": content,
                "status": status,
                "response_id": data.get("id"),
                "model": model,
                "raw_response": data
            }
            
    except Exception as e:
        logger.error(f"Error en web search nativo: {e}")
        return {
            "success": False,
            "error": str(e),
            "content": None
        }


async def call_llm_with_web_search_stream(
    model: str,
    messages: List[Dict],
    api_key: str,
    temperature: float = 0.7,
    base_url: str = "https://api.openai.com/v1"
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Llamar a OpenAI con Web Search nativo en modo streaming.
    
    Args:
        model: Nombre del modelo
        messages: Lista de mensajes
        api_key: OpenAI API key
        temperature: Temperatura
        base_url: URL base
    
    Yields:
        Dict con eventos del stream:
        - type: "token" | "web_search" | "done" | "error"
        - content: contenido del token o información
        - metadata: datos adicionales
    """
    
    url = f"{base_url}/chat/completions"
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "tools": [
            {
                "type": "web_search_preview"  # Correcto para OpenAI 2026
            }
        ],
        "stream": True
    }
    
    logger.info("Iniciando streaming con web search nativo", model=model)
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            ) as response:
                if response.status_code != 200:
                    error_msg = f"Error OpenAI API: {response.status_code}"
                    logger.error(error_msg)
                    yield {
                        "type": "error",
                        "content": error_msg,
                        "metadata": {}
                    }
                    return
                
                web_searches = []
                full_content = ""
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        
                        if data_str.strip() == "[DONE]":
                            yield {
                                "type": "done",
                                "content": full_content,
                                "metadata": {
                                    "web_searches": web_searches,
                                    "model": model
                                }
                            }
                            break
                        
                        try:
                            data = json.loads(data_str)
                            choice = data.get("choices", [{}])[0]
                            delta = choice.get("delta", {})
                            
                            # Token de contenido
                            content = delta.get("content", "")
                            if content:
                                full_content += content
                                yield {
                                    "type": "token",
                                    "content": content,
                                    "metadata": {}
                                }
                            
                            # Tool calls (web search)
                            tool_calls = delta.get("tool_calls", [])
                            for tool_call in tool_calls:
                                if tool_call.get("type") == "web_search":
                                    search_info = {
                                        "id": tool_call.get("id"),
                                        "query": tool_call.get("function", {}).get("arguments", {})
                                    }
                                    web_searches.append(search_info)
                                    yield {
                                        "type": "web_search",
                                        "content": f"🔍 Buscando: {search_info.get('query')}",
                                        "metadata": search_info
                                    }
                        
                        except json.JSONDecodeError:
                            continue
                
    except Exception as e:
        logger.error(f"Error en streaming con web search: {e}")
        yield {
            "type": "error",
            "content": str(e),
            "metadata": {}
        }


def is_web_search_supported(model: str) -> bool:
    """
    Verificar si un modelo soporta web search nativo.
    
    Args:
        model: Nombre del modelo
    
    Returns:
        True si el modelo soporta web search
    """
    supported_models = [
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-4-turbo-preview",
        "gpt-4o-search-preview",  # Modelo específico para web search
        "gpt-4o-mini-search-preview"  # Modelo mini para web search
    ]
    
    return any(supported in model.lower() for supported in supported_models)


def get_web_search_info() -> Dict[str, Any]:
    """
    Obtener información sobre el web search nativo de OpenAI.
    
    Returns:
        Dict con información sobre la funcionalidad
    """
    return {
        "provider": "OpenAI",
        "feature": "Native Web Search",
        "supported_models": [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4-turbo"
        ],
        "description": "Búsqueda web nativa integrada en OpenAI que usa Bing como motor de búsqueda.",
        "benefits": [
            "Sin necesidad de herramientas externas",
            "Integración nativa con el LLM",
            "Resultados actualizados de Bing",
            "Mejor comprensión del contexto"
        ],
        "limitations": [
            "Solo disponible en modelos específicos",
            "Requiere API key de OpenAI",
            "Costo por búsqueda incluido en tokens"
        ],
        "docs_url": "https://platform.openai.com/docs/guides/tools?tool-type=web-search"
    }
