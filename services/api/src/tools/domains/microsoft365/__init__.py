"""
Microsoft 365 Tools - Herramientas HTTP contra proxy-365.

Cada herramienta llama a un endpoint REST del proxy-365 (Microsoft Graph),
leyendo la configuracion de conexion (URL + token) de la tabla
openapi_connections (slug='microsoft-365').
"""

import time
import httpx
from typing import Dict, Any, List, Optional
from urllib.parse import quote

import structlog

logger = structlog.get_logger()

_connection_cache: Dict[str, Any] = {}
_CACHE_TTL_SECONDS = 300


def _invalidate_cache():
    _connection_cache.clear()


def _resolve_user_id(explicit: Optional[str], injected: Optional[str]) -> Optional[str]:
    """Resolve user_id: explicit param > injected _user_id from session."""
    return explicit or injected


async def _get_proxy_config() -> Dict[str, str]:
    cached_at = _connection_cache.get("_cached_at", 0)
    if _connection_cache.get("base_url") and (time.time() - cached_at) < _CACHE_TTL_SECONDS:
        return _connection_cache

    from src.db.repositories.openapi_connections import OpenAPIConnectionRepository
    conn = await OpenAPIConnectionRepository.get_by_slug("microsoft-365")

    if not conn:
        raise ValueError(
            "No existe conexion 'microsoft-365' en openapi_connections. "
            "Configure la conexion al proxy 365 en Tools > OpenAPI."
        )
    if not conn.is_active:
        raise ValueError("La conexion 'microsoft-365' esta desactivada.")

    _connection_cache["base_url"] = conn.base_url.rstrip("/")
    _connection_cache["token"] = conn.auth_token or ""
    _connection_cache["_cached_at"] = time.time()
    logger.info("M365 proxy config loaded", base_url=_connection_cache["base_url"])
    return _connection_cache


async def _proxy_request(
    method: str,
    path: str,
    params: Optional[Dict[str, str]] = None,
    json_body: Optional[Dict[str, Any]] = None,
    timeout: float = 30.0,
) -> Dict[str, Any]:
    config = await _get_proxy_config()
    url = f"{config['base_url']}{path}"
    headers = {}
    if config["token"]:
        headers["Authorization"] = f"Bearer {config['token']}"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if method.upper() == "GET":
                resp = await client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                resp = await client.post(url, headers=headers, json=json_body)
            else:
                resp = await client.request(method, url, headers=headers, json=json_body)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return {"data": data, "count": len(data)}
            return data
    except httpx.ConnectError:
        return {"success": False, "error": f"No se puede conectar al proxy 365 en {config['base_url']}."}
    except httpx.TimeoutException:
        return {"success": False, "error": f"Timeout al conectar con proxy 365 ({timeout}s)."}
    except httpx.HTTPStatusError as e:
        body = e.response.text[:500] if e.response else ""
        if e.response.status_code == 401:
            _invalidate_cache()
        return {"success": False, "error": f"Error HTTP {e.response.status_code}: {body}"}
    except Exception as e:
        return {"success": False, "error": f"Error inesperado: {str(e)}"}


# ── Mail ──────────────────────────────────────────────────────────

async def m365_mail_list(
    folder: Optional[str] = None,
    search: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    user_id: Optional[str] = None,
    _user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Lista mensajes de correo del buzón."""
    uid = _resolve_user_id(user_id, _user_id)
    if not uid:
        return {"error": "user_id requerido", "success": False}
    params: Dict[str, str] = {
        "userId": uid,
        # Seleccionar solo campos necesarios para listado (evita incluir body HTML completo
        # que infla la respuesta a cientos de KB y supera el límite de contexto del LLM).
        # bodyPreview incluye los primeros ~255 chars del cuerpo, suficiente para listar correos.
        "select": "id,subject,from,toRecipients,receivedDateTime,isRead,hasAttachments,bodyPreview,importance,parentFolderId,conversationId",
    }
    if folder:
        params["folder"] = folder
    if search:
        params["search"] = search
    if page is not None:
        params["page"] = str(page)
    params["pageSize"] = str(page_size if page_size is not None else 25)
    return await _proxy_request("GET", "/api/mail/messages", params=params)


async def m365_mail_get(
    message_id: str,
    user_id: Optional[str] = None,
    _user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Obtiene el contenido completo de un correo por su ID (incluye cuerpo HTML/texto)."""
    return await _proxy_request(
        "GET",
        f"/api/mail/messages/{quote(message_id)}",
        params={"userId": _resolve_user_id(user_id, _user_id)},
    )


async def m365_mail_attachments(
    message_id: str,
    user_id: Optional[str] = None,
    _user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Lista los adjuntos de un correo."""
    return await _proxy_request(
        "GET",
        f"/api/mail/messages/{quote(message_id)}/attachments",
        params={"userId": _resolve_user_id(user_id, _user_id)},
    )


async def m365_mail_folders(user_id: Optional[str] = None, _user_id: Optional[str] = None) -> Dict[str, Any]:
    """Lista carpetas de correo (Inbox, Sent, etc.)."""
    return await _proxy_request("GET", "/api/mail/folders", params={"userId": _resolve_user_id(user_id, _user_id)})


async def m365_mail_send(
    subject: str,
    body: str,
    to_recipients: List[str],
    content_type: str = "html",
    user_id: Optional[str] = None,
    _user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Envía un correo electrónico."""
    return await _proxy_request("POST", "/api/mail/send", json_body={
        "userId": _resolve_user_id(user_id, _user_id),
        "subject": subject,
        "body": {"contentType": content_type, "content": body},
        "toRecipients": to_recipients,
    })


# ── Calendar ──────────────────────────────────────────────────────

async def m365_calendar_list(user_id: Optional[str] = None, _user_id: Optional[str] = None) -> Dict[str, Any]:
    """Lista calendarios disponibles."""
    return await _proxy_request("GET", "/api/calendar/calendars", params={"userId": _resolve_user_id(user_id, _user_id)})


async def m365_calendar_events(
    start_date_time: Optional[str] = None,
    end_date_time: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    user_id: Optional[str] = None,
    _user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Lista eventos del calendario."""
    params: Dict[str, str] = {"userId": _resolve_user_id(user_id, _user_id)}
    if start_date_time:
        params["startDateTime"] = start_date_time
    if end_date_time:
        params["endDateTime"] = end_date_time
    if page is not None:
        params["page"] = str(page)
    if page_size is not None:
        params["pageSize"] = str(page_size)
    return await _proxy_request("GET", "/api/calendar/events", params=params)


async def m365_calendar_create_event(
    subject: str,
    start: Dict[str, str],
    end: Dict[str, str],
    location: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    user_id: Optional[str] = None,
    _user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Crea un evento en el calendario."""
    body: Dict[str, Any] = {"userId": _resolve_user_id(user_id, _user_id), "subject": subject, "start": start, "end": end}
    if location:
        body["location"] = location
    if attendees:
        body["attendees"] = attendees
    return await _proxy_request("POST", "/api/calendar/events", json_body=body)


# ── OneDrive ──────────────────────────────────────────────────────

async def m365_onedrive_root(user_id: Optional[str] = None, _user_id: Optional[str] = None) -> Dict[str, Any]:
    """Obtiene información de la raíz de OneDrive."""
    return await _proxy_request("GET", "/api/onedrive/root", params={"userId": _resolve_user_id(user_id, _user_id)})


async def m365_onedrive_list(
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    user_id: Optional[str] = None,
    _user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Lista archivos y carpetas de la raíz de OneDrive."""
    params: Dict[str, str] = {"userId": _resolve_user_id(user_id, _user_id)}
    if page is not None:
        params["page"] = str(page)
    if page_size is not None:
        params["pageSize"] = str(page_size)
    return await _proxy_request("GET", "/api/onedrive/root/children", params=params)


async def m365_onedrive_search(q: str) -> Dict[str, Any]:
    """Busca archivos en OneDrive."""
    return await _proxy_request("GET", "/api/onedrive/search", params={"q": q})


# ── Teams ─────────────────────────────────────────────────────────

async def m365_teams_list(user_id: Optional[str] = None, _user_id: Optional[str] = None) -> Dict[str, Any]:
    """Lista equipos de Microsoft Teams."""
    return await _proxy_request("GET", "/api/teams", params={"userId": _resolve_user_id(user_id, _user_id)})


async def m365_teams_chats(user_id: Optional[str] = None, _user_id: Optional[str] = None) -> Dict[str, Any]:
    """Lista chats del usuario en Teams."""
    return await _proxy_request("GET", "/api/teams/chats", params={"userId": _resolve_user_id(user_id, _user_id)})


async def m365_teams_channels(team_id: str) -> Dict[str, Any]:
    """Lista canales de un equipo."""
    return await _proxy_request("GET", f"/api/teams/{quote(team_id)}/channels")


async def m365_teams_members(team_id: str) -> Dict[str, Any]:
    """Lista miembros de un equipo."""
    return await _proxy_request("GET", f"/api/teams/{quote(team_id)}/members")


async def m365_teams_channel_messages(
    team_id: str,
    channel_id: str,
) -> Dict[str, Any]:
    """Lista mensajes de un canal."""
    return await _proxy_request(
        "GET", f"/api/teams/{quote(team_id)}/channels/{quote(channel_id)}/messages"
    )


async def m365_teams_send_message(
    team_id: str,
    channel_id: str,
    content: str,
    content_type: str = "html",
    subject: Optional[str] = None,
) -> Dict[str, Any]:
    """Envía un mensaje a un canal de Teams."""
    body: Dict[str, Any] = {"content": content, "contentType": content_type}
    if subject:
        body["subject"] = subject
    return await _proxy_request(
        "POST", f"/api/teams/{quote(team_id)}/channels/{quote(channel_id)}/messages",
        json_body=body,
    )


# ── Directory ─────────────────────────────────────────────────────

async def m365_directory_users(
    search: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
) -> Dict[str, Any]:
    """Lista usuarios del directorio Azure AD."""
    params: Dict[str, str] = {}
    if search:
        params["search"] = search
    if page is not None:
        params["page"] = str(page)
    if page_size is not None:
        params["pageSize"] = str(page_size)
    return await _proxy_request("GET", "/api/directory/users", params=params)


async def m365_directory_groups(
    page: Optional[int] = None,
    page_size: Optional[int] = None,
) -> Dict[str, Any]:
    """Lista grupos de Azure AD."""
    params: Dict[str, str] = {}
    if page is not None:
        params["page"] = str(page)
    if page_size is not None:
        params["pageSize"] = str(page_size)
    return await _proxy_request("GET", "/api/directory/groups", params=params)


async def m365_directory_group_members(group_id: str) -> Dict[str, Any]:
    """Lista miembros de un grupo."""
    return await _proxy_request("GET", f"/api/directory/groups/{quote(group_id)}/members")


# ══════════════════════════════════════════════════════════════════
# Tool Definitions
# ══════════════════════════════════════════════════════════════════

M365_TOOLS: Dict[str, Any] = {
    # ── Mail ──
    "m365_mail_list": {
        "id": "m365_mail_list",
        "name": "m365_mail_list",
        "description": "Lista mensajes de correo. Devuelve 25 por defecto. Filtra por carpeta o busca por texto.",
        "parameters": {
            "type": "object",
            "properties": {
                "folder": {"type": "string", "description": "Carpeta (ej: 'Inbox', 'SentItems', 'Drafts'). Omitir para Inbox."},
                "search": {"type": "string", "description": "Texto de busqueda en asunto/cuerpo."},
                "page": {"type": "integer", "description": "Pagina (empezando en 1)."},
                "page_size": {"type": "integer", "description": "Resultados por pagina (default 25, maximo recomendado 50)."},
            },
            "required": [],
        },
        "handler": m365_mail_list,
    },
    "m365_mail_get": {
        "id": "m365_mail_get",
        "name": "m365_mail_get",
        "description": "Lee el contenido completo de un correo por su ID: cuerpo HTML/texto, remitente, destinatarios y metadatos. Usar cuando el usuario quiera leer o analizar un correo concreto.",
        "parameters": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "ID del mensaje obtenido de m365_mail_list."},
            },
            "required": ["message_id"],
        },
        "handler": m365_mail_get,
    },
    "m365_mail_attachments": {
        "id": "m365_mail_attachments",
        "name": "m365_mail_attachments",
        "description": "Lista los adjuntos de un correo (nombre, tamaño, tipo MIME). Usar cuando el usuario pregunte por archivos adjuntos.",
        "parameters": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "ID del mensaje."},
            },
            "required": ["message_id"],
        },
        "handler": m365_mail_attachments,
    },
    "m365_mail_folders": {
        "id": "m365_mail_folders",
        "name": "m365_mail_folders",
        "description": "Lista carpetas de correo disponibles (Inbox, Sent Items, Drafts, etc.).",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "handler": m365_mail_folders,
    },
    "m365_mail_send": {
        "id": "m365_mail_send",
        "name": "m365_mail_send",
        "description": "Envia un correo electronico. Requiere destinatarios, asunto y cuerpo.",
        "parameters": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Asunto del correo."},
                "body": {"type": "string", "description": "Contenido del correo (HTML permitido)."},
                "to_recipients": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Lista de emails destinatarios.",
                },
                "content_type": {"type": "string", "enum": ["html", "text"], "description": "Tipo de contenido (default: html)."},
            },
            "required": ["subject", "body", "to_recipients"],
        },
        "handler": m365_mail_send,
    },
    # ── Calendar ──
    "m365_calendar_list": {
        "id": "m365_calendar_list",
        "name": "m365_calendar_list",
        "description": "Lista calendarios disponibles del usuario.",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "handler": m365_calendar_list,
    },
    "m365_calendar_events": {
        "id": "m365_calendar_events",
        "name": "m365_calendar_events",
        "description": "Lista eventos del calendario. Filtra por rango de fechas.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date_time": {"type": "string", "description": "Inicio del rango ISO 8601 (ej: '2026-02-17T00:00:00Z')."},
                "end_date_time": {"type": "string", "description": "Fin del rango ISO 8601 (ej: '2026-02-24T23:59:59Z')."},
                "page": {"type": "integer"},
                "page_size": {"type": "integer"},
            },
            "required": [],
        },
        "handler": m365_calendar_events,
    },
    "m365_calendar_create_event": {
        "id": "m365_calendar_create_event",
        "name": "m365_calendar_create_event",
        "description": "Crea un evento en el calendario. Requiere asunto, fecha/hora inicio y fin.",
        "parameters": {
            "type": "object",
            "properties": {
                "subject": {"type": "string", "description": "Titulo del evento."},
                "start": {
                    "type": "object", "description": "Inicio: {\"dateTime\": \"2026-02-20T10:00:00\", \"timeZone\": \"Europe/Madrid\"}.",
                },
                "end": {
                    "type": "object", "description": "Fin: {\"dateTime\": \"2026-02-20T11:00:00\", \"timeZone\": \"Europe/Madrid\"}.",
                },
                "location": {"type": "string", "description": "Ubicacion del evento."},
                "attendees": {"type": "array", "items": {"type": "string"}, "description": "Emails de asistentes."},
            },
            "required": ["subject", "start", "end"],
        },
        "handler": m365_calendar_create_event,
    },
    # ── OneDrive ──
    "m365_onedrive_root": {
        "id": "m365_onedrive_root",
        "name": "m365_onedrive_root",
        "description": "Obtiene informacion de la raiz de OneDrive (espacio usado, total, etc.).",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "handler": m365_onedrive_root,
    },
    "m365_onedrive_list": {
        "id": "m365_onedrive_list",
        "name": "m365_onedrive_list",
        "description": "Lista archivos y carpetas de la raiz de OneDrive.",
        "parameters": {
            "type": "object",
            "properties": {
                "page": {"type": "integer"},
                "page_size": {"type": "integer"},
            },
            "required": [],
        },
        "handler": m365_onedrive_list,
    },
    "m365_onedrive_search": {
        "id": "m365_onedrive_search",
        "name": "m365_onedrive_search",
        "description": "Busca archivos en OneDrive por nombre o contenido.",
        "parameters": {
            "type": "object",
            "properties": {
                "q": {"type": "string", "description": "Texto de busqueda."},
            },
            "required": ["q"],
        },
        "handler": m365_onedrive_search,
    },
    # ── Teams ──
    "m365_teams_list": {
        "id": "m365_teams_list",
        "name": "m365_teams_list",
        "description": "Lista equipos de Microsoft Teams del usuario.",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "handler": m365_teams_list,
    },
    "m365_teams_chats": {
        "id": "m365_teams_chats",
        "name": "m365_teams_chats",
        "description": "Lista chats recientes del usuario en Teams.",
        "parameters": {"type": "object", "properties": {}, "required": []},
        "handler": m365_teams_chats,
    },
    "m365_teams_channels": {
        "id": "m365_teams_channels",
        "name": "m365_teams_channels",
        "description": "Lista canales de un equipo de Teams.",
        "parameters": {
            "type": "object",
            "properties": {"team_id": {"type": "string", "description": "ID del equipo."}},
            "required": ["team_id"],
        },
        "handler": m365_teams_channels,
    },
    "m365_teams_members": {
        "id": "m365_teams_members",
        "name": "m365_teams_members",
        "description": "Lista miembros de un equipo de Teams.",
        "parameters": {
            "type": "object",
            "properties": {"team_id": {"type": "string", "description": "ID del equipo."}},
            "required": ["team_id"],
        },
        "handler": m365_teams_members,
    },
    "m365_teams_channel_messages": {
        "id": "m365_teams_channel_messages",
        "name": "m365_teams_channel_messages",
        "description": "Lista mensajes de un canal de Teams.",
        "parameters": {
            "type": "object",
            "properties": {
                "team_id": {"type": "string", "description": "ID del equipo."},
                "channel_id": {"type": "string", "description": "ID del canal."},
            },
            "required": ["team_id", "channel_id"],
        },
        "handler": m365_teams_channel_messages,
    },
    "m365_teams_send_message": {
        "id": "m365_teams_send_message",
        "name": "m365_teams_send_message",
        "description": "Envia un mensaje a un canal de Teams.",
        "parameters": {
            "type": "object",
            "properties": {
                "team_id": {"type": "string", "description": "ID del equipo."},
                "channel_id": {"type": "string", "description": "ID del canal."},
                "content": {"type": "string", "description": "Contenido del mensaje (HTML o texto)."},
                "content_type": {"type": "string", "enum": ["html", "text"], "description": "Tipo (default: html)."},
                "subject": {"type": "string", "description": "Asunto (opcional)."},
            },
            "required": ["team_id", "channel_id", "content"],
        },
        "handler": m365_teams_send_message,
    },
    # ── Directory ──
    "m365_directory_users": {
        "id": "m365_directory_users",
        "name": "m365_directory_users",
        "description": "Lista o busca usuarios en el directorio Azure AD de la empresa.",
        "parameters": {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Buscar por nombre o email."},
                "page": {"type": "integer"},
                "page_size": {"type": "integer"},
            },
            "required": [],
        },
        "handler": m365_directory_users,
    },
    "m365_directory_groups": {
        "id": "m365_directory_groups",
        "name": "m365_directory_groups",
        "description": "Lista grupos de Azure AD.",
        "parameters": {
            "type": "object",
            "properties": {
                "page": {"type": "integer"},
                "page_size": {"type": "integer"},
            },
            "required": [],
        },
        "handler": m365_directory_groups,
    },
    "m365_directory_group_members": {
        "id": "m365_directory_group_members",
        "name": "m365_directory_group_members",
        "description": "Lista miembros de un grupo de Azure AD.",
        "parameters": {
            "type": "object",
            "properties": {"group_id": {"type": "string", "description": "ID del grupo."}},
            "required": ["group_id"],
        },
        "handler": m365_directory_group_members,
    },
}
