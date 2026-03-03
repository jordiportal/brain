"""
OnlyOffice Document Server integration for Brain workspace files.

Generates editor configurations with JWT tokens so that OnlyOffice can
open documents stored in per-user sandboxes.
"""

import os
import time
import hashlib
import hmac
from typing import Optional, Dict, Any

import jwt
import structlog

logger = structlog.get_logger()

ONLYOFFICE_URL = os.getenv("ONLYOFFICE_URL", "")
ONLYOFFICE_PUBLIC_URL = os.getenv("ONLYOFFICE_PUBLIC_URL", "http://localhost:8088")
ONLYOFFICE_SECRET = os.getenv("ONLYOFFICE_SECRET", "")

OFFICE_EXTENSIONS = {
    "docx", "doc", "odt", "rtf", "txt",
    "xlsx", "xls", "csv", "ods",
    "pptx", "ppt", "ppsx", "odp",
}


def is_enabled() -> bool:
    return bool(ONLYOFFICE_URL and ONLYOFFICE_SECRET)


def is_office_file(filename: str) -> bool:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in OFFICE_EXTENSIONS


def _document_type(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in ("pptx", "ppt", "ppsx", "pps", "potx", "pot", "odp"):
        return "slide"
    if ext in ("xlsx", "xls", "csv", "ods"):
        return "cell"
    return "word"


def _file_type(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else "docx"


def generate_file_token(user_id: str, file_path: str) -> str:
    """Short-lived HMAC token for OnlyOffice to fetch a file without full auth."""
    ts = str(int(time.time()))
    msg = f"{user_id}:{file_path}:{ts}"
    sig = hmac.new(ONLYOFFICE_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{ts}.{sig}"


def verify_file_token(user_id: str, file_path: str, token: str) -> bool:
    """Verify the HMAC token (valid for 1 hour)."""
    try:
        ts_str, sig = token.split(".", 1)
        ts = int(ts_str)
        if time.time() - ts > 3600:
            return False
        msg = f"{user_id}:{file_path}:{ts_str}"
        expected = hmac.new(ONLYOFFICE_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()[:32]
        return hmac.compare_digest(sig, expected)
    except Exception:
        return False


def generate_editor_config(
    file_path: str,
    filename: str,
    file_url: str,
    user_id: str,
    user_name: str,
    callback_url: Optional[str] = None,
    mode: str = "edit",
    lang: str = "es",
) -> Dict[str, Any]:
    if not is_enabled():
        raise ValueError("OnlyOffice not configured")

    config: Dict[str, Any] = {
        "document": {
            "fileType": _file_type(filename),
            "key": hashlib.md5(f"{file_path}:{int(time.time())}".encode()).hexdigest()[:20],
            "title": filename,
            "url": file_url,
        },
        "documentType": _document_type(filename),
        "editorConfig": {
            "lang": lang,
            "mode": mode,
            "user": {"id": user_id, "name": user_name},
            "customization": {
                "autosave": True,
                "chat": False,
                "comments": False,
                "compactHeader": True,
                "feedback": False,
                "forcesave": True,
                "help": False,
            },
        },
    }

    if callback_url:
        config["editorConfig"]["callbackUrl"] = callback_url

    token = jwt.encode(config, ONLYOFFICE_SECRET, algorithm="HS256")
    config["token"] = token

    return {
        "config": config,
        "onlyoffice_url": ONLYOFFICE_PUBLIC_URL,
        "api_url": f"{ONLYOFFICE_PUBLIC_URL}/web-apps/apps/api/documents/api.js",
    }
