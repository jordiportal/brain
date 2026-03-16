"""
LLM call helper for memory extraction and summarization.

Uses task_llm_call for direct LLM calls bypassing the agent pipeline.
"""

import logging
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)

_EXTRACTION_SYSTEM = "You are a helpful assistant. Respond concisely and precisely. Follow the instructions exactly."


async def _default_llm_call(prompt: str) -> str:
    """
    Direct LLM call via the task model for fact extraction / episode summarization.
    """
    try:
        from ..task_llm import task_llm_call
        result = await task_llm_call(_EXTRACTION_SYSTEM, prompt, max_tokens=500)
        if result:
            return result
    except Exception as e:
        logger.debug(f"task_llm_call failed for memory: {e}")

    # Fallback: direct call_llm with the active provider
    try:
        from ...providers.llm_provider import get_active_llm_provider
        from ..chains.llm_utils import call_llm

        provider = await get_active_llm_provider()
        if not provider:
            logger.warning("No active LLM provider for memory extraction")
            return ""

        return await call_llm(
            llm_url=provider.base_url or "",
            model=provider.default_model or "qwen3:8b",
            messages=[
                {"role": "system", "content": _EXTRACTION_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
            provider_type=provider.type or "ollama",
            api_key=provider.api_key,
        )
    except Exception as e:
        logger.warning(f"LLM call for memory failed: {e}")
        return ""


def make_llm_call() -> Callable[[str], Awaitable[str]]:
    """
    Create an async callable that performs a lightweight LLM call.
    Used by MemoryManager.save_interaction for fact extraction and episodic summaries.
    """
    return _default_llm_call
