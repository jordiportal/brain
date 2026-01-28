"""
OpenAI-Compatible API for Brain

Expone Brain como un modelo compatible con la API de OpenAI,
permitiendo usar Brain desde cualquier cliente que soporte OpenAI SDK.

Endpoints:
- POST /v1/chat/completions - Chat completion
- GET /v1/models - List available models
- GET /v1/models/{model} - Get model details
"""

from .router import router

__all__ = ["router"]
