"""
LLM Utilities - Funciones de utilidad para llamar a LLMs desde las cadenas.
Soporta múltiples proveedores: Ollama, OpenAI, Anthropic, Groq, Azure.
"""

import json
from typing import List, Dict, AsyncGenerator, Optional
import httpx


async def call_llm(
    llm_url: str,
    model: str,
    messages: List[Dict],
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    provider_type: str = "ollama",
    api_key: Optional[str] = None
) -> str:
    """
    Llamar al LLM y obtener respuesta.
    Detecta el tipo de proveedor y usa la API correcta.
    
    Args:
        llm_url: URL base del proveedor
        model: Nombre del modelo
        messages: Lista de mensajes [{"role": "user", "content": "..."}]
        temperature: Temperatura para generación
        max_tokens: Máximo de tokens (opcional)
        provider_type: Tipo de proveedor ("ollama", "openai", "anthropic", "groq", "azure")
        api_key: API key para proveedores que lo requieren
    
    Returns:
        Contenido de la respuesta del LLM
    """
    provider = provider_type.lower()
    
    if provider == "ollama":
        return await _call_ollama(llm_url, model, messages, temperature, max_tokens)
    elif provider in ["openai", "groq", "azure"]:
        if not api_key:
            raise ValueError(f"API key requerida para {provider}")
        return await _call_openai_compatible(llm_url, model, messages, temperature, max_tokens, api_key)
    elif provider == "anthropic":
        if not api_key:
            raise ValueError("API key requerida para Anthropic")
        return await _call_anthropic(model, messages, temperature, max_tokens, api_key)
    else:
        # Fallback a Ollama para proveedores desconocidos
        return await _call_ollama(llm_url, model, messages, temperature, max_tokens)


async def call_llm_stream(
    llm_url: str,
    model: str,
    messages: List[Dict],
    temperature: float = 0.7,
    provider_type: str = "ollama",
    api_key: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Llamar al LLM con streaming.
    
    Args:
        llm_url: URL base del proveedor
        model: Nombre del modelo
        messages: Lista de mensajes
        temperature: Temperatura para generación
        provider_type: Tipo de proveedor
        api_key: API key (si es necesario)
    
    Yields:
        Tokens de la respuesta
    """
    provider = provider_type.lower()
    
    if provider == "ollama":
        async for token in _stream_ollama(llm_url, model, messages, temperature):
            yield token
    elif provider in ["openai", "groq", "azure"]:
        if not api_key:
            raise ValueError(f"API key requerida para {provider}")
        async for token in _stream_openai_compatible(llm_url, model, messages, temperature, api_key):
            yield token
    elif provider == "anthropic":
        if not api_key:
            raise ValueError("API key requerida para Anthropic")
        async for token in _stream_anthropic(model, messages, temperature, api_key):
            yield token
    else:
        # Fallback a Ollama
        async for token in _stream_ollama(llm_url, model, messages, temperature):
            yield token


# ===========================================
# Implementaciones por proveedor
# ===========================================

async def _call_ollama(
    base_url: str,
    model: str,
    messages: List[Dict],
    temperature: float,
    max_tokens: Optional[int]
) -> str:
    """Llamar a Ollama API"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{base_url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    **({"num_predict": max_tokens} if max_tokens else {})
                }
            }
        )
        data = response.json()
        return data.get("message", {}).get("content", "")


async def _call_openai_compatible(
    base_url: str,
    model: str,
    messages: List[Dict],
    temperature: float,
    max_tokens: Optional[int],
    api_key: str
) -> str:
    """Llamar a API compatible con OpenAI (OpenAI, Groq, Azure, etc.)"""
    url = f"{base_url}/chat/completions"
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False
    }
    
    if max_tokens:
        payload["max_tokens"] = max_tokens
    
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
            raise Exception(f"Error OpenAI API: {response.text}")
        
        data = response.json()
        choice = data.get("choices", [{}])[0]
        return choice.get("message", {}).get("content", "")


async def _call_anthropic(
    model: str,
    messages: List[Dict],
    temperature: float,
    max_tokens: Optional[int],
    api_key: str
) -> str:
    """Llamar a Anthropic Claude API"""
    # Separar system message del resto
    system_content = ""
    chat_messages = []
    
    for msg in messages:
        if msg["role"] == "system":
            system_content = msg["content"]
        else:
            chat_messages.append(msg)
    
    payload = {
        "model": model,
        "messages": chat_messages,
        "max_tokens": max_tokens or 4096,
        "temperature": temperature
    }
    
    if system_content:
        payload["system"] = system_content
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"Error Anthropic: {response.text}")
        
        data = response.json()
        return data.get("content", [{}])[0].get("text", "")


async def _stream_ollama(
    base_url: str,
    model: str,
    messages: List[Dict],
    temperature: float
) -> AsyncGenerator[str, None]:
    """Streaming desde Ollama"""
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream(
            "POST",
            f"{base_url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": True,
                "options": {"temperature": temperature}
            }
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue


async def _stream_openai_compatible(
    base_url: str,
    model: str,
    messages: List[Dict],
    temperature: float,
    api_key: str
) -> AsyncGenerator[str, None]:
    """Streaming desde API compatible con OpenAI"""
    url = f"{base_url}/chat/completions"
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream(
            "POST",
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "stream": True
            }
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue


async def _stream_anthropic(
    model: str,
    messages: List[Dict],
    temperature: float,
    api_key: str
) -> AsyncGenerator[str, None]:
    """Streaming desde Anthropic"""
    # Separar system message
    system_content = ""
    chat_messages = []
    
    for msg in messages:
        if msg["role"] == "system":
            system_content = msg["content"]
        else:
            chat_messages.append(msg)
    
    payload = {
        "model": model,
        "messages": chat_messages,
        "max_tokens": 4096,
        "temperature": temperature,
        "stream": True
    }
    
    if system_content:
        payload["system"] = system_content
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream(
            "POST",
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json=payload
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]
                    try:
                        data = json.loads(data_str)
                        event_type = data.get("type", "")
                        
                        if event_type == "content_block_delta":
                            delta = data.get("delta", {})
                            text = delta.get("text", "")
                            if text:
                                yield text
                        elif event_type == "message_stop":
                            break
                    except json.JSONDecodeError:
                        continue
