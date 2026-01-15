"""
LLM Router - Endpoints para interacción con LLMs
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, AsyncGenerator
import httpx
import json

router = APIRouter(prefix="/llm", tags=["LLM"])


class ChatMessage(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str


class ChatRequest(BaseModel):
    provider_url: str = "http://host.docker.internal:11434"
    model: str = "llama3.2"
    messages: List[ChatMessage]
    temperature: float = 0.7
    max_tokens: Optional[int] = None


class ChatResponse(BaseModel):
    content: str
    model: str
    tokens_used: Optional[int] = None


class TestConnectionRequest(BaseModel):
    provider_url: str
    model: Optional[str] = None


class TestConnectionResponse(BaseModel):
    success: bool
    message: str
    models: Optional[List[str]] = None


@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_llm_connection(request: TestConnectionRequest):
    """Probar conexión con un proveedor LLM"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Intentar obtener lista de modelos (Ollama)
            response = await client.get(f"{request.provider_url}/api/tags")
            
            if response.status_code == 200:
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                return TestConnectionResponse(
                    success=True,
                    message=f"Conexión exitosa. {len(models)} modelos disponibles.",
                    models=models
                )
            else:
                return TestConnectionResponse(
                    success=False,
                    message=f"Error: HTTP {response.status_code}"
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
        # Preparar mensajes para Ollama
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{request.provider_url}/api/chat",
                json={
                    "model": request.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": request.temperature,
                        **({"num_predict": request.max_tokens} if request.max_tokens else {})
                    }
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return ChatResponse(
                    content=data.get("message", {}).get("content", ""),
                    model=request.model,
                    tokens_used=data.get("eval_count")
                )
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Error del LLM: {response.text}"
                )
                
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Timeout: El LLM tardó demasiado en responder")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="No se puede conectar al servidor LLM")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
                "options": {
                    "temperature": temperature
                }
            }
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            # Formato SSE
                            yield f"data: {json.dumps({'content': content})}\n\n"
                        
                        # Si es el último mensaje, enviar done
                        if data.get("done", False):
                            yield f"data: {json.dumps({'done': True, 'total_tokens': data.get('eval_count', 0)})}\n\n"
                    except json.JSONDecodeError:
                        continue


@router.post("/chat/stream")
async def chat_with_llm_stream(request: ChatRequest):
    """Enviar mensaje al LLM y obtener respuesta con streaming (SSE)"""
    try:
        # Preparar mensajes para Ollama
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        
        return StreamingResponse(
            stream_ollama_response(
                request.provider_url,
                request.model,
                messages,
                request.temperature
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_models(provider_url: str = "http://host.docker.internal:11434"):
    """Listar modelos disponibles en el proveedor"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{provider_url}/api/tags")
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "models": [
                        {
                            "name": m["name"],
                            "size": m.get("size"),
                            "modified_at": m.get("modified_at")
                        }
                        for m in data.get("models", [])
                    ]
                }
            else:
                raise HTTPException(status_code=response.status_code, detail="Error obteniendo modelos")
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
