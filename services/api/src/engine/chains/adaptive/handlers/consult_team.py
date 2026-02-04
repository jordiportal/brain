"""
Handler para la tool `consult_team_member`.

Maneja consultas a miembros del equipo (modo Brain Team):
obtiene opinión/propuesta del experto sin ejecutar la tarea completa.
"""

from .base import ToolHandler, ToolResult


class ConsultTeamMemberHandler(ToolHandler):
    """
    Handler para consult_team_member (coordinador Brain Team).
    Inyecta config LLM igual que DelegateHandler.
    """

    tool_name = "consult_team_member"
    display_name = "👥 Consultando miembro del equipo"
    is_terminal = False

    def prepare_args(self, args: dict) -> dict:
        """Inyecta configuración LLM para el subagente consultado."""
        prepared = args.copy()
        if self.llm_config:
            prepared["_llm_url"] = self.llm_config.get("url")
            prepared["_model"] = self.llm_config.get("model")
            prepared["_provider_type"] = self.llm_config.get("provider")
            prepared["_api_key"] = self.llm_config.get("api_key")
        return prepared

    async def process_result(self, result: dict, args: dict) -> ToolResult:
        """Procesa la respuesta de la consulta al miembro del equipo."""
        if not result.get("success"):
            return ToolResult(
                success=False,
                data=result,
                message_content=result.get("error", "Error en consulta")
            )
        response_text = result.get("response", "")
        agent_name = result.get("agent_name", args.get("agent", "unknown"))
        message = f"[{agent_name}]: {response_text}" if agent_name else response_text
        return ToolResult(
            success=True,
            data=result,
            message_content=message or str(result)[:16000]
        )
