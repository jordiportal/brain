"""
Pydantic Models for OpenAI-Compatible API

Define los modelos de request/response siguiendo la especificación de OpenAI.
"""

from typing import Optional, List, Dict, Any, Union, Literal
from pydantic import BaseModel, Field
from datetime import datetime
import time


# ============================================
# Chat Completion Request Models
# ============================================

class ChatMessage(BaseModel):
    """Mensaje en una conversación de chat"""
    role: Literal["system", "user", "assistant", "tool", "function"]
    content: Optional[str] = None
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class FunctionDefinition(BaseModel):
    """Definición de una función para tool calling"""
    name: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class ToolDefinition(BaseModel):
    """Definición de una herramienta"""
    type: Literal["function"] = "function"
    function: FunctionDefinition


class ResponseFormat(BaseModel):
    """Formato de respuesta"""
    type: Literal["text", "json_object", "json_schema"] = "text"
    json_schema: Optional[Dict[str, Any]] = None


class StreamOptions(BaseModel):
    """Opciones de streaming"""
    include_usage: bool = False


class ChatCompletionRequest(BaseModel):
    """Request para /v1/chat/completions"""
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2)
    top_p: Optional[float] = Field(default=1.0, ge=0, le=1)
    n: Optional[int] = Field(default=1, ge=1, le=10)
    stream: Optional[bool] = False
    stream_options: Optional[StreamOptions] = None
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = Field(default=None, ge=1)
    max_completion_tokens: Optional[int] = None
    presence_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    frequency_penalty: Optional[float] = Field(default=0, ge=-2, le=2)
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    tools: Optional[List[ToolDefinition]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    response_format: Optional[ResponseFormat] = None
    seed: Optional[int] = None


# ============================================
# Chat Completion Response Models
# ============================================

class ToolCall(BaseModel):
    """Tool call en la respuesta"""
    id: str
    type: Literal["function"] = "function"
    function: Dict[str, Any]


class ChatCompletionMessage(BaseModel):
    """Mensaje de respuesta del assistant"""
    role: Literal["assistant"] = "assistant"
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    refusal: Optional[str] = None


class ChatCompletionChoice(BaseModel):
    """Una opción de completion"""
    index: int
    message: ChatCompletionMessage
    finish_reason: Literal["stop", "length", "tool_calls", "content_filter", None]
    logprobs: Optional[Dict[str, Any]] = None


class CompletionUsage(BaseModel):
    """Estadísticas de uso de tokens"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_tokens_details: Optional[Dict[str, int]] = None
    completion_tokens_details: Optional[Dict[str, int]] = None


class ChatCompletionResponse(BaseModel):
    """Response para /v1/chat/completions"""
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[CompletionUsage] = None
    system_fingerprint: Optional[str] = None
    service_tier: Optional[str] = "default"


# ============================================
# Streaming Response Models
# ============================================

class ChatCompletionChunkDelta(BaseModel):
    """Delta de contenido en streaming"""
    role: Optional[str] = None
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ChatCompletionChunkChoice(BaseModel):
    """Choice en streaming"""
    index: int
    delta: ChatCompletionChunkDelta
    finish_reason: Optional[Literal["stop", "length", "tool_calls", "content_filter"]] = None
    logprobs: Optional[Dict[str, Any]] = None


class ChatCompletionChunk(BaseModel):
    """Chunk de streaming"""
    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionChunkChoice]
    usage: Optional[CompletionUsage] = None
    system_fingerprint: Optional[str] = None


# ============================================
# Models Endpoint
# ============================================

class ModelInfo(BaseModel):
    """Información de un modelo"""
    id: str
    object: Literal["model"] = "model"
    created: int = Field(default_factory=lambda: int(time.time()))
    owned_by: str = "brain"


class ModelsListResponse(BaseModel):
    """Response para /v1/models"""
    object: Literal["list"] = "list"
    data: List[ModelInfo]


# ============================================
# Error Response
# ============================================

class ErrorDetail(BaseModel):
    """Detalle de error"""
    message: str
    type: str
    param: Optional[str] = None
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Response de error estilo OpenAI"""
    error: ErrorDetail
