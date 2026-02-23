"""
OpenAI-Compatible API Router

Implementa endpoints compatibles con la API de OpenAI para exponer Brain
como un "modelo" que puede ser consumido por cualquier cliente OpenAI.

Endpoints:
- POST /v1/chat/completions
- GET /v1/models
- GET /v1/models/{model}
"""

import json
import time
import uuid
from typing import Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException, Header, Request, Depends
from fastapi.responses import StreamingResponse, JSONResponse
import structlog

from .models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatCompletionMessage,
    CompletionUsage,
    ChatCompletionChunk,
    ChatCompletionChunkChoice,
    ChatCompletionChunkDelta,
    ModelsListResponse,
    ModelInfo,
    ErrorResponse,
    ErrorDetail
)
from .auth import api_key_validator
from .oauth import oauth_validator
from .config import config_loader, BackendLLM

from ..engine.registry import chain_registry
from ..engine.models import ChainConfig

logger = structlog.get_logger()

router = APIRouter(tags=["OpenAI Compatible"])


# ============================================
# Helper: Cargar proveedor LLM de la cadena
# ============================================

async def _get_chain_llm_provider(chain_id: str) -> Optional[BackendLLM]:
    """
    Carga el proveedor LLM asociado a una cadena desde la BD.
    
    Returns:
        BackendLLM configurado o None si no hay proveedor asociado
    """
    try:
        from ..db.repositories.chains import ChainRepository
        
        chain = await ChainRepository.get_by_slug(chain_id)
        if chain and chain.llm_provider:
            p = chain.llm_provider
            logger.info(
                f"Chain {chain_id} has LLM provider: {p.name} ({p.type})",
                provider_id=p.id,
                model=p.default_model
            )
            return BackendLLM(
                provider=p.type or "ollama",
                url=p.base_url or "",
                model=p.default_model or "",
                api_key=p.api_key
            )
    except Exception as e:
        logger.warning(f"Could not load chain LLM provider: {e}")
    
    return None


# ============================================
# Dependency: Dual Authentication (API Key + OAuth)
# ============================================

async def verify_auth(authorization: Optional[str] = Header(None)) -> dict:
    """
    Dual-mode auth dependency.

    - Bearer sk-brain-* → API key validation (existing flow)
    - Bearer eyJ*         → Microsoft Entra ID JWT validation (OAuth)
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "Missing Authorization header",
                    "type": "invalid_request_error",
                    "code": "missing_api_key"
                }
            }
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "Invalid Authorization header format. Expected 'Bearer <token>'",
                    "type": "invalid_request_error",
                    "code": "invalid_api_key"
                }
            }
        )

    token = parts[1]

    # --- Path A: Brain API Key ---
    if token.startswith("sk-brain-"):
        key_data = await api_key_validator.validate_key(token)
        if not key_data:
            raise HTTPException(
                status_code=401,
                detail={"error": {"message": "Invalid API key", "type": "invalid_request_error", "code": "invalid_api_key"}}
            )
        user_id = key_data.get("permissions", {}).get("default_user_id")
        return {
            "auth_type": "apikey",
            "key_data": key_data,
            "api_key": token,
            "user_id": user_id,
        }

    # --- Path B: OAuth JWT (Microsoft Entra ID) ---
    if await oauth_validator.is_enabled():
        try:
            claims = await oauth_validator.validate_token(token)
            return {
                "auth_type": "oauth",
                "key_data": None,
                "api_key": None,
                "user_id": claims.user_id,
                "user_name": claims.name,
                "oauth_claims": claims,
            }
        except ValueError as e:
            logger.warning("OAuth token validation failed", error=str(e))
            raise HTTPException(
                status_code=401,
                detail={"error": {"message": str(e), "type": "authentication_error", "code": "invalid_token"}}
            )

    # Token doesn't match any known auth method
    raise HTTPException(
        status_code=401,
        detail={"error": {"message": "Invalid credentials. Provide a valid API key (sk-brain-*) or OAuth token.", "type": "invalid_request_error", "code": "invalid_api_key"}}
    )


# ============================================
# POST /v1/chat/completions
# ============================================

@router.post("/v1/chat/completions")
async def create_chat_completion(
    request: ChatCompletionRequest,
    auth: dict = Depends(verify_auth)
):
    """
    Creates a model response for the given chat conversation.
    
    Compatible con la API de OpenAI /v1/chat/completions.
    Internamente ejecuta la cadena Brain correspondiente al modelo solicitado.
    Acepta autenticación por API key (sk-brain-*) o JWT de Microsoft Entra ID.
    """
    key_data = auth.get("key_data")
    api_key = auth.get("api_key")
    auth_type = auth.get("auth_type", "apikey")
    
    logger.info(
        "OpenAI-compat chat completion request",
        model=request.model,
        messages_count=len(request.messages),
        stream=request.stream,
        auth_type=auth_type,
        key_name=key_data.get("name") if key_data else None,
        user_id=auth.get("user_id"),
    )
    
    config = await config_loader.load_config()
    
    if not config.is_enabled:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "message": "Brain API is currently disabled",
                    "type": "service_unavailable",
                    "code": "api_disabled"
                }
            }
        )
    
    # Model permission check
    model_allowed = True
    if auth_type == "apikey" and key_data:
        model_allowed = api_key_validator.check_model_permission(key_data, request.model)
    elif auth_type == "oauth":
        model_allowed = await oauth_validator.check_model_permission(request.model)

    if not model_allowed:
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "message": f"No permission to use model '{request.model}'",
                    "type": "permission_denied",
                    "code": "model_not_allowed"
                }
            }
        )
    
    model_config = config_loader.get_model(request.model)
    if not model_config:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": f"Model '{request.model}' not found",
                    "type": "invalid_request_error",
                    "code": "model_not_found"
                }
            }
        )
    
    completion_id = f"chatcmpl-brain-{uuid.uuid4().hex[:24]}"
    
    # Resolve user_id: explicit in request > auth-resolved > key default
    user_id = request.user or auth.get("user_id")
    
    if request.stream:
        return StreamingResponse(
            stream_chat_completion(
                request=request,
                completion_id=completion_id,
                model_config=model_config,
                backend_config=config.backend_llm,
                api_key=api_key,
                key_data=key_data,
                user_id=user_id,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    return await execute_chat_completion(
        request=request,
        completion_id=completion_id,
        model_config=model_config,
        backend_config=config.backend_llm,
        api_key=api_key,
        key_data=key_data,
        user_id=user_id
    )


async def execute_chat_completion(
    request: ChatCompletionRequest,
    completion_id: str,
    model_config,
    backend_config,
    api_key: str,
    key_data: dict,
    user_id: Optional[str] = None,
) -> ChatCompletionResponse:
    """Ejecuta una chat completion sin streaming"""
    
    start_time = time.time()
    
    # Cargar proveedor de la cadena (si tiene uno asignado)
    chain_llm_provider = await _get_chain_llm_provider(model_config.chain_id)
    if chain_llm_provider:
        backend_config = chain_llm_provider
        logger.info(f"Using chain's LLM provider: {backend_config.provider}/{backend_config.model}")
    
    # Convertir mensajes al formato interno
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    
    # Obtener el último mensaje del usuario
    user_message = ""
    for msg in reversed(messages):
        if msg["role"] == "user":
            user_message = msg["content"]
            break
    
    # Obtener builder de la cadena
    chain_id = model_config.chain_id
    builder = chain_registry.get_builder(chain_id)
    definition = chain_registry.get(chain_id)
    
    if not builder or not definition:
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Chain '{chain_id}' not found in registry",
                    "type": "internal_error",
                    "code": "chain_not_found"
                }
            }
        )
    
    # Preparar input para la cadena
    chain_input = {
        "message": user_message,
        "query": user_message
    }
    
    # Ejecutar la cadena
    try:
        full_response = ""
        tools_used = []
        
        async for event in builder(
            config=definition.config,
            llm_url=backend_config.url,
            model=backend_config.model,
            input_data=chain_input,
            memory=messages[:-1],  # Todos los mensajes excepto el último
            execution_id=completion_id,
            stream=False,
            provider_type=backend_config.provider,
            api_key=backend_config.api_key,
            user_id=user_id,
        ):
            # Capturar resultado
            if isinstance(event, dict) and "_result" in event:
                result = event["_result"]
                full_response = result.get("response", "")
                tools_used = result.get("tools_used", [])
                break
            
            # Capturar tokens si no hay _result
            if hasattr(event, 'event_type'):
                if event.event_type == "token" and event.content:
                    full_response += event.content
                elif event.event_type == "response_complete" and event.content:
                    full_response = event.content
        
        # Calcular tokens (aproximación)
        prompt_tokens = sum(len(m.content or "") // 4 for m in request.messages)
        completion_tokens = len(full_response) // 4
        total_tokens = prompt_tokens + completion_tokens
        
        if api_key:
            await api_key_validator.update_usage(api_key, total_tokens)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "Chat completion completed",
            completion_id=completion_id,
            tokens=total_tokens,
            elapsed_ms=elapsed_ms
        )
        
        return ChatCompletionResponse(
            id=completion_id,
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatCompletionMessage(
                        role="assistant",
                        content=full_response
                    ),
                    finish_reason="stop"
                )
            ],
            usage=CompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens
            )
        )
        
    except Exception as e:
        logger.error(f"Error executing chain: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Error executing model: {str(e)}",
                    "type": "internal_error",
                    "code": "execution_error"
                }
            }
        )


async def stream_chat_completion(
    request: ChatCompletionRequest,
    completion_id: str,
    model_config,
    backend_config,
    api_key: str,
    key_data: dict,
    user_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Genera streaming de chat completion en formato SSE"""
    
    start_time = time.time()
    
    # Cargar proveedor de la cadena (si tiene uno asignado)
    chain_llm_provider = await _get_chain_llm_provider(model_config.chain_id)
    if chain_llm_provider:
        backend_config = chain_llm_provider
        logger.info(f"Using chain's LLM provider: {backend_config.provider}/{backend_config.model}")
    
    # Convertir mensajes
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    
    # Obtener el último mensaje del usuario
    user_message = ""
    for msg in reversed(messages):
        if msg["role"] == "user":
            user_message = msg["content"]
            break
    
    # Obtener builder de la cadena
    chain_id = model_config.chain_id
    builder = chain_registry.get_builder(chain_id)
    definition = chain_registry.get(chain_id)
    
    if not builder or not definition:
        error_chunk = {
            "error": {
                "message": f"Chain '{chain_id}' not found",
                "type": "internal_error"
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"
        return
    
    # Enviar chunk inicial con role
    initial_chunk = ChatCompletionChunk(
        id=completion_id,
        created=int(time.time()),
        model=request.model,
        choices=[
            ChatCompletionChunkChoice(
                index=0,
                delta=ChatCompletionChunkDelta(role="assistant"),
                finish_reason=None
            )
        ]
    )
    yield f"data: {initial_chunk.model_dump_json()}\n\n"
    
    # Preparar input
    chain_input = {
        "message": user_message,
        "query": user_message
    }
    
    total_tokens = 0
    
    # Activar Brain Events para modelos brain-* (Open WebUI)
    emit_brain_events = request.model.startswith("brain-")
    
    try:
        async for event in builder(
            config=definition.config,
            llm_url=backend_config.url,
            model=backend_config.model,
            input_data=chain_input,
            memory=messages[:-1],
            execution_id=completion_id,
            stream=True,
            provider_type=backend_config.provider,
            api_key=backend_config.api_key,
            emit_brain_events=emit_brain_events,
            user_id=user_id,
        ):
            # Streaming de tokens
            if hasattr(event, 'event_type') and event.event_type == "token" and event.content:
                content_chunk = ChatCompletionChunk(
                    id=completion_id,
                    created=int(time.time()),
                    model=request.model,
                    choices=[
                        ChatCompletionChunkChoice(
                            index=0,
                            delta=ChatCompletionChunkDelta(content=event.content),
                            finish_reason=None
                        )
                    ]
                )
                yield f"data: {content_chunk.model_dump_json()}\n\n"
                total_tokens += 1
        
        # Chunk final
        final_chunk = ChatCompletionChunk(
            id=completion_id,
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChunkChoice(
                    index=0,
                    delta=ChatCompletionChunkDelta(),
                    finish_reason="stop"
                )
            ]
        )
        yield f"data: {final_chunk.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"
        
        if api_key:
            await api_key_validator.update_usage(api_key, total_tokens)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "Streaming completion finished",
            completion_id=completion_id,
            elapsed_ms=elapsed_ms
        )
        
    except Exception as e:
        logger.error(f"Error in streaming: {e}", exc_info=True)
        error_chunk = {
            "error": {
                "message": str(e),
                "type": "internal_error"
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"


# ============================================
# GET /v1/models
# ============================================

@router.get("/v1/models")
async def list_models(auth: dict = Depends(verify_auth)):
    """
    Lists the currently available models.
    
    Compatible con la API de OpenAI /v1/models.
    """
    key_data = auth.get("key_data")
    
    config = await config_loader.load_config()
    
    # Filter by permissions
    models = []
    for model in config.available_models:
        if key_data:
            if not api_key_validator.check_model_permission(key_data, model.id):
                continue
        elif auth.get("auth_type") == "oauth":
            if not await oauth_validator.check_model_permission(model.id):
                continue
        models.append(ModelInfo(
            id=model.id,
            created=int(time.time()),
            owned_by="brain"
        ))
    
    logger.info(
        "Models list requested",
        models_count=len(models),
        auth_type=auth.get("auth_type"),
    )
    
    return ModelsListResponse(data=models)


@router.get("/v1/models/{model_id}")
async def get_model(model_id: str, auth: dict = Depends(verify_auth)):
    """
    Retrieves a model instance.
    
    Compatible con la API de OpenAI /v1/models/{model}.
    """
    key_data = auth.get("key_data")
    
    config = await config_loader.load_config()
    model_config = config_loader.get_model(model_id)
    
    if not model_config:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": f"Model '{model_id}' not found",
                    "type": "invalid_request_error",
                    "code": "model_not_found"
                }
            }
        )
    
    model_allowed = True
    if key_data:
        model_allowed = api_key_validator.check_model_permission(key_data, model_id)
    elif auth.get("auth_type") == "oauth":
        model_allowed = await oauth_validator.check_model_permission(model_id)

    if not model_allowed:
        raise HTTPException(
            status_code=403,
            detail={
                "error": {
                    "message": f"Access denied to model '{model_id}'",
                    "type": "permission_denied",
                    "code": "model_not_allowed"
                }
            }
        )
    
    return ModelInfo(
        id=model_config.id,
        created=int(time.time()),
        owned_by="brain"
    )


# ============================================
# Management Endpoints (no requieren auth OpenAI)
# ============================================

@router.get("/v1/brain/status")
async def get_brain_status():
    """Estado de la API Brain (público, sin auth)"""
    config = await config_loader.load_config()
    
    return {
        "status": "online" if config.is_enabled else "disabled",
        "version": "2.0.0",
        "models_available": len(config.available_models),
        "default_model": config.default_model
    }
