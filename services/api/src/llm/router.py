"""
LLM Router - Endpoints para interacción con LLMs
Soporta múltiples proveedores: Ollama, OpenAI, Anthropic, etc.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, AsyncGenerator
import httpx
import json

router = APIRouter(prefix="/llm", tags=["LLM"])


# ===========================================
# Modelos de Request/Response
# ===========================================

class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str


class ChatRequest(BaseModel):
    provider_url: str = "http://host.docker.internal:11434"
    provider_type: str = "ollama"  # "ollama", "openai", "anthropic", "azure", "groq"
    model: str = "llama3.2"
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    api_key: Optional[str] = None  # Para proveedores que requieren API key


class ChatResponse(BaseModel):
    content: str
    model: str
    tokens_used: Optional[int] = None


class TestConnectionRequest(BaseModel):
    provider_url: str
    provider_type: str = "ollama"
    api_key: Optional[str] = None
    model: Optional[str] = None


class TestConnectionResponse(BaseModel):
    success: bool
    message: str
    models: Optional[List[str]] = None


class ListModelsRequest(BaseModel):
    provider_url: str
    provider_type: str = "ollama"
    api_key: Optional[str] = None


# ===========================================
# Funciones auxiliares por proveedor
# ===========================================

async def get_ollama_models(base_url: str) -> List[str]:
    """Obtener modelos de Ollama"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{base_url}/api/tags")
        if response.status_code == 200:
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
    return []


async def get_openai_models(base_url: str, api_key: str) -> List[str]:
    """Obtener modelos de OpenAI"""
    # OpenAI API URL base es https://api.openai.com/v1
    url = f"{base_url}/models"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"}
        )
        if response.status_code == 200:
            data = response.json()
            # Filtrar solo modelos de chat (GPT y serie o)
            models = [m["id"] for m in data.get("data", [])]
            # Incluir modelos GPT (3.5, 4, 4o, 5, etc.) y serie o (o1, o3, o4, etc.)
            chat_models = [m for m in models if any(x in m for x in ["gpt-5", "gpt-4", "gpt-3.5", "o1-", "o3-", "o4-"])]
            return sorted(chat_models, reverse=True)
    return []


async def get_anthropic_models(api_key: str) -> List[str]:
    """Obtener modelos de Anthropic (lista estática, no tienen endpoint de modelos)"""
    return [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307"
    ]


async def get_groq_models(api_key: str) -> List[str]:
    """Obtener modelos de Groq"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"}
        )
        if response.status_code == 200:
            data = response.json()
            return [m["id"] for m in data.get("data", [])]
    return []


async def get_gemini_models(base_url: str, api_key: str) -> List[str]:
    """Obtener modelos de Google Gemini"""
    url = f"{base_url}/models?key={api_key}"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            models = []
            for model in data.get("models", []):
                name = model.get("name", "").replace("models/", "")
                # Filtrar solo modelos Gemini de chat (no embeddings, ni gemma)
                if name.startswith("gemini-") and "embedding" not in name.lower():
                    # Verificar que soporte generateContent
                    methods = model.get("supportedGenerationMethods", [])
                    if "generateContent" in methods:
                        models.append(name)
            return sorted(models, reverse=True)
    return []


# ===========================================
# Funciones de Chat por proveedor
# ===========================================

async def chat_ollama(
    base_url: str,
    model: str,
    messages: List[dict],
    temperature: float,
    max_tokens: Optional[int] = None,
    stream: bool = False
) -> dict:
    """Chat con Ollama"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{base_url}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": stream,
                "options": {
                    "temperature": temperature,
                    **({"num_predict": max_tokens} if max_tokens else {})
                }
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "content": data.get("message", {}).get("content", ""),
                "tokens": data.get("eval_count")
            }
        else:
            raise Exception(f"Error Ollama: {response.text}")


async def chat_openai(
    base_url: str,
    model: str,
    messages: List[dict],
    temperature: float,
    max_tokens: Optional[int],
    api_key: str,
    stream: bool = False
) -> dict:
    """Chat con OpenAI API (compatible con OpenAI, Azure, Groq, etc.)"""
    url = f"{base_url}/chat/completions"
    
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": stream
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
        
        if response.status_code == 200:
            data = response.json()
            choice = data.get("choices", [{}])[0]
            usage = data.get("usage", {})
            return {
                "content": choice.get("message", {}).get("content", ""),
                "tokens": usage.get("total_tokens")
            }
        else:
            raise Exception(f"Error OpenAI API: {response.text}")


async def chat_anthropic(
    model: str,
    messages: List[dict],
    temperature: float,
    max_tokens: Optional[int],
    api_key: str
) -> dict:
    """Chat con Anthropic Claude API"""
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
        
        if response.status_code == 200:
            data = response.json()
            content = data.get("content", [{}])[0].get("text", "")
            usage = data.get("usage", {})
            return {
                "content": content,
                "tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
            }
        else:
            raise Exception(f"Error Anthropic: {response.text}")


async def chat_gemini(
    base_url: str,
    model: str,
    messages: List[dict],
    temperature: float,
    max_tokens: Optional[int],
    api_key: str
) -> dict:
    """Chat con Google Gemini API"""
    # Convertir mensajes de OpenAI format a Gemini format
    gemini_contents = []
    system_instruction = None
    
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        
        if role == "system":
            system_instruction = content
        elif role == "user":
            gemini_contents.append({
                "role": "user",
                "parts": [{"text": content}]
            })
        elif role == "assistant":
            gemini_contents.append({
                "role": "model",
                "parts": [{"text": content}]
            })
    
    payload = {
        "contents": gemini_contents,
        "generationConfig": {
            "temperature": temperature,
            "topK": 40,
            "topP": 0.95,
        }
    }
    
    if max_tokens:
        payload["generationConfig"]["maxOutputTokens"] = max_tokens
    
    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }
    
    url = f"{base_url}/models/{model}:generateContent?key={api_key}"
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            url,
            headers={"Content-Type": "application/json"},
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"Error Gemini API: {response.text}")
        
        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise Exception("No se generó respuesta")
        
        content_parts = candidates[0].get("content", {}).get("parts", [])
        if not content_parts:
            raise Exception("Respuesta vacía")
        
        content = content_parts[0].get("text", "")
        usage = data.get("usageMetadata", {})
        
        return {
            "content": content,
            "tokens": usage.get("totalTokenCount")
        }


# ===========================================
# Streaming por proveedor
# ===========================================

async def stream_ollama_response(
    provider_url: str,
    model: str,
    messages: List[dict],
    temperature: float
) -> AsyncGenerator[str, None]:
    """Generador asíncrono para streaming de respuestas de Ollama"""
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream(
            "POST",
            f"{provider_url}/api/chat",
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
                            yield f"data: {json.dumps({'content': content})}\n\n"
                        
                        if data.get("done", False):
                            yield f"data: {json.dumps({'done': True, 'total_tokens': data.get('eval_count', 0)})}\n\n"
                    except json.JSONDecodeError:
                        continue


async def stream_openai_response(
    base_url: str,
    model: str,
    messages: List[dict],
    temperature: float,
    api_key: str
) -> AsyncGenerator[str, None]:
    """Generador asíncrono para streaming de OpenAI API"""
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
                        yield f"data: {json.dumps({'done': True})}\n\n"
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield f"data: {json.dumps({'content': content})}\n\n"
                    except json.JSONDecodeError:
                        continue


async def stream_gemini_response(
    base_url: str,
    model: str,
    messages: List[dict],
    temperature: float,
    api_key: str
) -> AsyncGenerator[str, None]:
    """
    Generador asíncrono para streaming de Gemini API.
    
    NOTA: Gemini devuelve UN array de objetos completo formateado en múltiples líneas,
    NO múltiples JSON objects separados como OpenAI.
    """
    # Convertir mensajes a formato Gemini
    gemini_contents = []
    system_instruction = None
    
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        
        if role == "system":
            system_instruction = content
        elif role == "user":
            gemini_contents.append({
                "role": "user",
                "parts": [{"text": content}]
            })
        elif role == "assistant":
            gemini_contents.append({
                "role": "model",
                "parts": [{"text": content}]
            })
    
    payload = {
        "contents": gemini_contents,
        "generationConfig": {
            "temperature": temperature,
            "topK": 40,
            "topP": 0.95,
        }
    }
    
    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }
    
    url = f"{base_url}/models/{model}:streamGenerateContent?key={api_key}"
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream(
            "POST",
            url,
            headers={"Content-Type": "application/json"},
            json=payload
        ) as response:
            # Acumular todas las líneas para formar el JSON completo
            accumulated_lines = []
            async for line in response.aiter_lines():
                accumulated_lines.append(line)
            
            # Unir todas las líneas y parsear como JSON
            full_response = "\n".join(accumulated_lines)
            
            try:
                # Gemini devuelve un array de chunks
                chunks = json.loads(full_response)
                
                # Procesar cada chunk
                total_tokens = 0
                for chunk in chunks:
                    candidates = chunk.get("candidates", [])
                    if candidates:
                        content_parts = candidates[0].get("content", {}).get("parts", [])
                        if content_parts:
                            text = content_parts[0].get("text", "")
                            if text:
                                # Enviar texto en streaming
                                yield f"data: {json.dumps({'content': text})}\n\n"
                    
                    # Obtener metadata de tokens del último chunk
                    usage = chunk.get("usageMetadata", {})
                    if usage:
                        total_tokens = usage.get("totalTokenCount", 0)
                
                # Enviar evento done
                yield f"data: {json.dumps({'done': True, 'total_tokens': total_tokens})}\n\n"
                
            except json.JSONDecodeError as e:
                # Si falla el parsing, enviar error
                yield f"data: {json.dumps({'error': f'Error parsing Gemini response: {str(e)}'})}\n\n"


# ===========================================
# Endpoints
# ===========================================

@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_llm_connection(request: TestConnectionRequest):
    """Probar conexión con un proveedor LLM"""
    try:
        models = []
        provider_type = request.provider_type.lower()
        
        if provider_type == "ollama":
            models = await get_ollama_models(request.provider_url)
        elif provider_type == "openai":
            if not request.api_key:
                return TestConnectionResponse(
                    success=False,
                    message="API Key requerida para OpenAI"
                )
            models = await get_openai_models(request.provider_url, request.api_key)
        elif provider_type == "anthropic":
            if not request.api_key:
                return TestConnectionResponse(
                    success=False,
                    message="API Key requerida para Anthropic"
                )
            models = await get_anthropic_models(request.api_key)
        elif provider_type == "groq":
            if not request.api_key:
                return TestConnectionResponse(
                    success=False,
                    message="API Key requerida para Groq"
                )
            models = await get_groq_models(request.api_key)
        elif provider_type == "gemini":
            if not request.api_key:
                return TestConnectionResponse(
                    success=False,
                    message="API Key requerida para Gemini"
                )
            models = await get_gemini_models(request.provider_url, request.api_key)
        else:
            # Para proveedores custom, intentar como Ollama primero
            try:
                models = await get_ollama_models(request.provider_url)
            except:
                pass
        
        if models:
            return TestConnectionResponse(
                success=True,
                message=f"Conexión exitosa. {len(models)} modelos disponibles.",
                models=models
            )
        else:
            return TestConnectionResponse(
                success=False,
                message="No se pudieron obtener los modelos. Verifica la configuración."
            )
            
    except httpx.TimeoutException:
        return TestConnectionResponse(
            success=False,
            message="Error: Timeout - El servidor no responde"
        )
    except httpx.ConnectError:
        return TestConnectionResponse(
            success=False,
            message="Error: No se puede conectar al servidor"
        )
    except Exception as e:
        return TestConnectionResponse(
            success=False,
            message=f"Error: {str(e)}"
        )


@router.post("/chat", response_model=ChatResponse)
async def chat_with_llm(request: ChatRequest):
    """Enviar mensaje al LLM y obtener respuesta (sin streaming)"""
    try:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        provider_type = request.provider_type.lower()
        
        result = None
        
        if provider_type == "ollama":
            result = await chat_ollama(
                request.provider_url,
                request.model,
                messages,
                request.temperature,
                request.max_tokens
            )
        elif provider_type in ["openai", "groq", "azure"]:
            if not request.api_key:
                raise HTTPException(status_code=400, detail="API Key requerida")
            result = await chat_openai(
                request.provider_url,
                request.model,
                messages,
                request.temperature,
                request.max_tokens,
                request.api_key
            )
        elif provider_type == "anthropic":
            if not request.api_key:
                raise HTTPException(status_code=400, detail="API Key requerida")
            result = await chat_anthropic(
                request.model,
                messages,
                request.temperature,
                request.max_tokens,
                request.api_key
            )
        elif provider_type == "gemini":
            if not request.api_key:
                raise HTTPException(status_code=400, detail="API Key requerida")
            result = await chat_gemini(
                request.provider_url,
                request.model,
                messages,
                request.temperature,
                request.max_tokens,
                request.api_key
            )
        else:
            # Fallback a Ollama para proveedores custom
            result = await chat_ollama(
                request.provider_url,
                request.model,
                messages,
                request.temperature,
                request.max_tokens
            )
        
        return ChatResponse(
            content=result["content"],
            model=request.model,
            tokens_used=result.get("tokens")
        )
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Timeout: El LLM tardó demasiado en responder")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="No se puede conectar al servidor LLM")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_with_llm_stream(request: ChatRequest):
    """Enviar mensaje al LLM y obtener respuesta con streaming (SSE)"""
    try:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        provider_type = request.provider_type.lower()
        
        if provider_type in ["openai", "groq", "azure"]:
            if not request.api_key:
                raise HTTPException(status_code=400, detail="API Key requerida")
            generator = stream_openai_response(
                request.provider_url,
                request.model,
                messages,
                request.temperature,
                request.api_key
            )
        elif provider_type == "gemini":
            if not request.api_key:
                raise HTTPException(status_code=400, detail="API Key requerida")
            generator = stream_gemini_response(
                request.provider_url,
                request.model,
                messages,
                request.temperature,
                request.api_key
            )
        else:
            # Ollama y custom
            generator = stream_ollama_response(
                request.provider_url,
                request.model,
                messages,
                request.temperature
            )
        
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/models")
async def list_models(request: ListModelsRequest):
    """Listar modelos disponibles en el proveedor"""
    try:
        models = []
        provider_type = request.provider_type.lower()
        
        if provider_type == "ollama":
            models = await get_ollama_models(request.provider_url)
        elif provider_type == "openai":
            if not request.api_key:
                raise HTTPException(status_code=400, detail="API Key requerida para OpenAI")
            models = await get_openai_models(request.provider_url, request.api_key)
        elif provider_type == "anthropic":
            models = await get_anthropic_models(request.api_key or "")
        elif provider_type == "groq":
            if not request.api_key:
                raise HTTPException(status_code=400, detail="API Key requerida para Groq")
            models = await get_groq_models(request.api_key)
        elif provider_type == "gemini":
            if not request.api_key:
                raise HTTPException(status_code=400, detail="API Key requerida para Gemini")
            models = await get_gemini_models(request.provider_url, request.api_key)
        else:
            # Intentar como Ollama
            try:
                models = await get_ollama_models(request.provider_url)
            except:
                pass
        
        return {"models": [{"name": m} for m in models]}
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Mantener endpoint GET para compatibilidad
@router.get("/models")
async def list_models_get(
    provider_url: str = "http://host.docker.internal:11434",
    provider_type: str = "ollama",
    api_key: Optional[str] = None
):
    """Listar modelos disponibles (GET para compatibilidad)"""
    request = ListModelsRequest(
        provider_url=provider_url,
        provider_type=provider_type,
        api_key=api_key
    )
    return await list_models(request)
