"""Ejecutor calendar_briefing: eventos hoy/mañana de proxy-365 -> LLM -> resultado."""

from datetime import date, timedelta

import asyncpg

from .base import call_llm, call_proxy365, save_result


async def run_calendar_briefing(pool: asyncpg.Pool, task_id: int, user_id: str, name: str) -> None:
    today = date.today()
    tomorrow = today + timedelta(days=1)
    params = {
        "userId": user_id,
        "start": today.isoformat(),
        "end": (tomorrow + timedelta(days=1)).isoformat(),
    }
    data = await call_proxy365("/api/calendar/events", params)
    events = data.get("data") or data.get("value") or data.get("events") or []

    if not events:
        await save_result(pool, task_id, user_id, "calendar_briefing", "Agenda", "No hay eventos para hoy ni mañana.")
        return

    lines = []
    for ev in events:
        start = (ev.get("start") or {}).get("dateTime") or str(ev.get("start"))
        end = (ev.get("end") or {}).get("dateTime") or str(ev.get("end"))
        subject = ev.get("subject") or ev.get("title") or "(sin título)"
        lines.append(f"- **{start}** - **{end}**: {subject}")

    user_content = "Eventos de hoy y mañana:\n\n" + "\n\n".join(lines)
    system_content = (
        "Eres un asistente que presenta la agenda. Genera un briefing breve en markdown: "
        "agrupa por día, destaca reuniones importantes. Máximo 1 página."
    )
    content = await call_llm(user_id, system_content, user_content)
    await save_result(pool, task_id, user_id, "calendar_briefing", "Agenda", content or "Sin contenido.")
