"""
Microsoft 365 Assistant Agent - Productividad con Microsoft 365.

Subagente especializado en:
- Correo (Outlook): lectura, búsqueda, envío
- Calendario: consulta de agenda, creación de eventos
- OneDrive: exploración y búsqueda de archivos
- Microsoft Teams: equipos, canales, mensajes
- Directorio (Azure AD): usuarios, grupos
"""

import time
from pathlib import Path
from typing import Optional

import structlog

from ..base import BaseSubAgent, SubAgentResult, Skill

logger = structlog.get_logger()


def _read_system_prompt() -> str:
    path = Path(__file__).parent / "prompts" / "system_prompt.txt"
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return (
            "Eres un Asistente de Productividad Microsoft 365. "
            "Usa las herramientas m365_* para gestionar correo, calendario, "
            "OneDrive, Teams y directorio corporativo. "
            "NUNCA inventes datos: usa siempre los datos reales obtenidos de las herramientas."
        )


M365_SKILLS = [
    Skill(
        id="m365_productivity",
        name="Microsoft 365 Productivity",
        description="Referencia completa de todas las herramientas M365, patrones de uso y mejores prácticas. CARGAR SIEMPRE.",
    ),
    Skill(
        id="email_management",
        name="Gestión de Correo",
        description="Estrategias de búsqueda de correo, plantillas HTML y reglas de envío",
    ),
    Skill(
        id="calendar_teams",
        name="Calendario y Teams",
        description="Gestión de agenda, creación de eventos, envío de mensajes Teams",
    ),
]


class M365AssistantAgent(BaseSubAgent):
    """
    Subagente especializado en productividad Microsoft 365.
    
    Conecta al proxy-365 via HTTP para interactuar con Microsoft Graph API.
    """

    id = "m365_assistant"
    name = "Microsoft 365 Assistant"
    description = "Asistente M365: correo, calendario, OneDrive, Teams, directorio corporativo y tareas programadas (automatizaciones personales)"
    version = "1.0.0"
    domain_tools = [
        "m365_mail_list",
        "m365_mail_get",
        "m365_mail_attachments",
        "m365_mail_folders",
        "m365_mail_send",
        "m365_calendar_list",
        "m365_calendar_events",
        "m365_calendar_create_event",
        "m365_onedrive_root",
        "m365_onedrive_list",
        "m365_onedrive_search",
        "m365_teams_list",
        "m365_teams_chats",
        "m365_teams_channels",
        "m365_teams_members",
        "m365_teams_channel_messages",
        "m365_teams_send_message",
        "m365_directory_users",
        "m365_directory_groups",
        "m365_directory_group_members",
        "user_tasks_list",
        "user_tasks_create",
        "user_tasks_update",
        "user_tasks_delete",
        "user_tasks_run_now",
        "user_tasks_results",
    ]
    available_skills = M365_SKILLS

    role = "Asistente de Productividad Microsoft 365 y Automatizaciones Personales"
    expertise = "Experto en gestión de correo, calendario, archivos, Teams, directorio corporativo via Microsoft Graph, y tareas programadas del usuario (automatizaciones, cron jobs, briefings)"
    task_requirements = "Consultas sobre correo, calendario, archivos OneDrive, Teams, directorio corporativo, o tareas programadas / automatizaciones personales"

    def __init__(self):
        super().__init__()
        self.system_prompt = _read_system_prompt()
        logger.info("📧 M365AssistantAgent initialized (shared loop)")

    async def execute(
        self,
        task: str,
        context: Optional[str] = None,
        session_id: Optional[str] = None,
        llm_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_type: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> SubAgentResult:
        start_time = time.time()
        logger.info("📧 M365AssistantAgent executing", task=task[:80], session_id=session_id)
        if not llm_url or not model or not provider_type:
            return SubAgentResult(
                success=False,
                response="**Error:** Se requiere configuración LLM para este agente.\n\nPor favor, configure un modelo LLM en la sección de Configuración.",
                agent_id=self.id,
                agent_name=self.name,
                error="LLM_NOT_CONFIGURED",
                execution_time_ms=0,
            )
        try:
            return await super().execute(
                task=task,
                context=context,
                session_id=session_id,
                llm_url=llm_url,
                model=model,
                provider_type=provider_type,
                api_key=api_key,
            )
        except Exception as e:
            logger.error(f"M365AssistantAgent error: {e}", exc_info=True)
            return SubAgentResult(
                success=False,
                response=f"**Error en M365 Assistant:** {str(e)}",
                agent_id=self.id,
                agent_name=self.name,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )


m365_assistant = M365AssistantAgent()
