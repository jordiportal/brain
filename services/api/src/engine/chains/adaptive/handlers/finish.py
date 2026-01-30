"""
Handler para la tool `finish`.

La tool finish termina la ejecución del agente con una respuesta final.
"""

from .base import ToolHandler, ToolResult
from ....models import StreamEvent


class FinishHandler(ToolHandler):
    """
    Handler para la tool finish.
    Siempre es terminal - termina la ejecución del agente.
    """
    
    tool_name = "finish"
    display_name = "✅ Finalizando"
    is_terminal = True
    
    async def process_result(self, result: dict, args: dict) -> ToolResult:
        """
        Procesa el resultado de finish.
        
        Args:
            result: Resultado de la tool (contiene final_answer)
            args: Argumentos (puede contener answer o final_answer)
        """
        # Extraer respuesta final
        final_answer = (
            result.get("final_answer") or 
            result.get("answer") or 
            args.get("final_answer") or 
            args.get("answer") or 
            ""
        )
        
        # Crear eventos
        events = []
        
        # Evento de token con la respuesta
        if final_answer:
            events.append(self.create_token_event(final_answer))
        
        return ToolResult(
            success=True,
            data={"final_answer": final_answer},
            is_terminal=True,
            final_answer=final_answer,
            events=events,
            message_content=final_answer
        )
