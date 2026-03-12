"""
Task LLM — Direct LLM calls for lightweight maintenance tasks
(title generation, follow-up suggestions).

These bypass the agent pipeline entirely and call the LLM provider
configured in brain_settings.task_model.
"""

import json
import logging
from typing import Optional

from src.db.repositories.brain_settings import BrainSettingsRepository
from src.db.repositories.llm_providers import LLMProviderRepository
from src.engine.chains.llm_utils import call_llm

logger = logging.getLogger(__name__)

_TITLE_SYSTEM = (
    "You are a title generator. Given a user message, respond with ONLY a JSON object.\n"
    "Rules:\n"
    "- Generate a concise 3-5 word title with an emoji at the start.\n"
    "- The title must clearly represent the main theme.\n"
    "- Write in the message's language; default to English if unclear.\n"
    "- Output ONLY: {\"title\": \"emoji + title\"}\n"
    "- No explanation, no extra text."
)

_FOLLOW_UP_SYSTEM = (
    "You are a follow-up question generator. Given a conversation, respond with ONLY a JSON object.\n"
    "Rules:\n"
    "- Suggest 3 relevant follow-up questions from the user's perspective.\n"
    "- Make them concise and directly related to the topic.\n"
    "- Use the conversation's language; default to English.\n"
    "- Output ONLY: {\"follow_ups\": [\"Q1?\", \"Q2?\", \"Q3?\"]}\n"
    "- No explanation, no extra text."
)


async def get_task_model_config() -> Optional[dict]:
    """
    Read the task_model setting and resolve the LLM provider.
    Returns {"url", "model", "provider_type", "api_key"} or None.
    """
    cfg = await BrainSettingsRepository.get("task_model")
    if not cfg or not isinstance(cfg, dict):
        return None

    provider_id = cfg.get("provider_id")
    model_name = cfg.get("model", "")
    if not provider_id or not model_name:
        return None

    provider = await LLMProviderRepository.get_by_id(int(provider_id))
    if not provider or not provider.base_url:
        logger.warning("task_model provider_id=%s not found or missing base_url", provider_id)
        return None

    return {
        "url": provider.base_url.rstrip("/"),
        "model": model_name,
        "provider_type": provider.type or "openai",
        "api_key": provider.api_key,
    }


async def task_llm_call(system: str, user_content: str, max_tokens: int = 250) -> Optional[str]:
    """
    Single-shot LLM call using the task model.
    Returns the raw response text or None if not configured / fails.
    """
    cfg = await get_task_model_config()
    if not cfg:
        return None

    try:
        return await call_llm(
            llm_url=cfg["url"],
            model=cfg["model"],
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            temperature=0.4,
            max_tokens=max_tokens,
            provider_type=cfg["provider_type"],
            api_key=cfg["api_key"],
        )
    except Exception as exc:
        logger.warning("task_llm_call failed: %s", exc)
        return None


def _parse_json_field(text: str, field: str):
    """Extract a field from a JSON string embedded in LLM output."""
    start = text.find("{")
    end = text.rfind("}") + 1
    if start < 0 or end <= start:
        return None
    try:
        return json.loads(text[start:end]).get(field)
    except (json.JSONDecodeError, AttributeError):
        return None


async def generate_title(user_message: str) -> Optional[str]:
    """Generate a short title with emoji for a conversation."""
    raw = await task_llm_call(_TITLE_SYSTEM, user_message[:300], max_tokens=60)
    if not raw:
        return None

    title = _parse_json_field(raw, "title")
    if title and isinstance(title, str):
        return title.strip()[:120]

    cleaned = raw.strip().strip('"').strip("'")[:120]
    return cleaned if cleaned else None


async def generate_follow_ups(messages: list[dict], count: int = 3) -> Optional[list[str]]:
    """Generate follow-up question suggestions from recent messages."""
    formatted = "\n".join(
        f"{m.get('role', 'user')}: {(m.get('content') or '')[:200]}"
        for m in messages[-6:]
    )
    raw = await task_llm_call(_FOLLOW_UP_SYSTEM, formatted, max_tokens=250)
    if not raw:
        return None

    follow_ups = _parse_json_field(raw, "follow_ups")
    if isinstance(follow_ups, list):
        return [q.strip() for q in follow_ups if isinstance(q, str) and q.strip()][:count]
    return None
