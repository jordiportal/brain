"""
Inyecta briefing pendiente y personal_prompt en el contexto del agente.
Se llama desde agent.py durante la construcción de messages[].
"""

import structlog

from src.db.repositories.user_task_results import UserTaskResultRepository
from src.db.repositories.user_profiles import UserProfileRepository

logger = structlog.get_logger()


async def get_pending_briefing(user_id: str) -> str | None:
    """Lee user_task_results con is_read=false, construye markdown y marca como leídos."""
    try:
        results = await UserTaskResultRepository.get_unread(user_id)
        if not results:
            return None
        sections = [f"### {r['title']}\n{r['content']}" for r in results]
        await UserTaskResultRepository.mark_as_read(user_id)
        logger.info("Briefing injected", user_id=user_id, items=len(results))
        return "\n\n".join(sections)
    except Exception as e:
        logger.warning("Failed to load briefing", user_id=user_id, error=str(e))
        return None


async def get_personal_prompt(user_id: str) -> str | None:
    """Devuelve el personal_prompt del perfil del usuario."""
    try:
        profile = await UserProfileRepository.get(user_id)
        if not profile or not profile.get("personal_prompt"):
            return None
        return profile["personal_prompt"]
    except Exception as e:
        logger.warning("Failed to load personal prompt", user_id=user_id, error=str(e))
        return None


async def apply_user_context(
    user_id: str | None,
    messages: list[dict],
    system_prompt: str,
) -> str:
    """Inyecta briefing + personal_prompt. Devuelve el system_prompt extendido.
    - Agrega mensaje system con briefing si hay resultados no leídos.
    - Extiende system_prompt con instrucciones personales.
    """
    logger.debug("context_injector.apply_user_context", user_id=user_id)
    if not user_id:
        return system_prompt

    briefing = await get_pending_briefing(user_id)
    if briefing:
        messages.append({
            "role": "system",
            "content": f"NOVEDADES DESDE LA ÚLTIMA SESIÓN DEL USUARIO:\n\n{briefing}",
        })

    personal = await get_personal_prompt(user_id)
    if personal:
        system_prompt += f"\n\n## INSTRUCCIONES PERSONALES DEL USUARIO\n{personal}"

    return system_prompt
