"""
LLM call helper for memory extraction and summarization.

Provides a lightweight async function that calls the active LLM
without going through the full agent pipeline.
"""

import logging
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)


async def _default_llm_call(prompt: str) -> str:
    """
    Make a lightweight LLM call using the adaptive chain builder.
    This is used for fact extraction and episode summarization.
    """
    try:
        from ..chains.adaptive.agent import build_adaptive_agent
        from ..models import ChainConfig
        from ...providers.llm_provider import get_active_llm_provider

        provider = await get_active_llm_provider()
        if not provider:
            logger.warning("No active LLM provider for memory extraction")
            return ""

        config = ChainConfig(
            system_prompt="You are a helpful assistant. Respond concisely and precisely.",
            model=provider.default_model or "qwen3:8b",
            temperature=0.3,
            max_iterations=1,
        )

        response = ""
        async for event in build_adaptive_agent(
            config=config,
            llm_url=provider.base_url or "",
            model=config.model,
            input_data={"message": prompt, "query": prompt},
            memory=[],
            execution_id="memory-extraction",
            stream=False,
            provider_type=provider.type or "ollama",
            api_key=provider.api_key,
        ):
            if isinstance(event, dict) and "_result" in event:
                response = event["_result"].get("response", "")
                break

        return response
    except Exception as e:
        logger.warning(f"LLM call for memory failed: {e}")
        return ""


def make_llm_call() -> Callable[[str], Awaitable[str]]:
    """
    Create an async callable that performs a lightweight LLM call.
    Used by MemoryManager.save_interaction for fact extraction and episodic summaries.
    """
    return _default_llm_call
