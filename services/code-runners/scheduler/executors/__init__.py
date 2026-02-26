"""Task executor registry. Signature: (db_path, task_id, user_id, name)."""

from .mail_digest import run_mail_digest
from .calendar_briefing import run_calendar_briefing

_REGISTRY = {
    "mail_digest": run_mail_digest,
    "calendar_briefing": run_calendar_briefing,
}


def get_executor(task_type: str):
    return _REGISTRY.get(task_type)
