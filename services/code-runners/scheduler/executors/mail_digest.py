"""Ejecutor mail_digest: correos de proxy-365 + preferencias -> LLM -> resultado."""

import json

from .base import call_llm, call_proxy365, get_user_profile, save_result

MAIL_SELECT = "id,subject,from,toRecipients,receivedDateTime,isRead,hasAttachments,bodyPreview,importance"


async def run_mail_digest(db_path: str, task_id: int, user_id: str, name: str) -> None:
    profile = await get_user_profile(db_path, user_id)
    prefs = (profile or {}).get("preferences") or {}
    if isinstance(prefs, str):
        prefs = json.loads(prefs) if prefs else {}
    important_senders = prefs.get("importantSenders") or []
    project_keywords = prefs.get("projectKeywords") or []

    params = {"userId": user_id, "select": MAIL_SELECT, "pageSize": "25"}
    data = await call_proxy365("/api/mail/messages", params)
    messages = data.get("data") or data.get("value") or data.get("messages") or []

    if not messages:
        await save_result(db_path, task_id, user_id, "mail_summary", "Resumen de correo", "No hay correos nuevos.")
        return

    lines = []
    for m in messages[:20]:
        from_addr = (m.get("from") or {}).get("emailAddress") or {}
        from_email = from_addr.get("address") or "?"
        subj = m.get("subject") or "(sin asunto)"
        date = m.get("receivedDateTime", "")[:19]
        preview = (m.get("bodyPreview") or "")[:200]
        lines.append(f"- **{date}** | {from_email}\n  Asunto: {subj}\n  Vista previa: {preview}")

    user_content = "Correos recientes:\n\n" + "\n\n".join(lines)
    if important_senders:
        user_content += f"\n\nRemitentes importantes: {', '.join(important_senders)}"
    if project_keywords:
        user_content += f"\n\nPalabras clave de proyectos: {', '.join(project_keywords)}"

    system_content = (
        "Eres un asistente que resume el correo. Genera un resumen breve en markdown: "
        "título por remitente o tema, puntos clave, y si hay algo que requiera acción. "
        "Sé conciso (máximo 1 página)."
    )
    content = await call_llm(user_id, system_content, user_content)
    await save_result(db_path, task_id, user_id, "mail_summary", "Resumen de correo", content or "Sin contenido.")
