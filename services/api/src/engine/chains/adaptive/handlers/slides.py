"""
Handler para la tool `generate_slides`.

Genera presentaciones HTML con streaming de Brain Events.
Esta tool es terminal - termina la ejecución tras éxito.
"""

from .base import ToolHandler, ToolResult
from ....models import StreamEvent


class SlidesHandler(ToolHandler):
    """
    Handler para generación de presentaciones.
    Es terminal - termina la ejecución del agente tras éxito.
    """
    
    tool_name = "generate_slides"
    display_name = "📊 Generando presentación"
    is_terminal = True  # Siempre termina tras éxito
    
    def prepare_args(self, args: dict) -> dict:
        """Inyecta configuración LLM."""
        prepared = args.copy()
        
        if self.llm_config:
            prepared["_llm_url"] = self.llm_config.get("url")
            prepared["_model"] = self.llm_config.get("model")
            prepared["_provider_type"] = self.llm_config.get("provider")
            prepared["_api_key"] = self.llm_config.get("api_key")
        
        return prepared
    
    async def process_result(self, result: dict, args: dict) -> ToolResult:
        """
        Procesa el resultado de generate_slides.
        
        Los eventos ya vienen generados por la tool, solo los reempaquetamos.
        """
        events = []
        brain_events = []
        
        # Emitir eventos capturados
        if self.emit_brain_events:
            events_emitted = result.get("events_emitted", [])
            for event_marker in events_emitted:
                events.append(StreamEvent(
                    event_type="token",
                    execution_id=self.execution_id,
                    node_id="slides_streaming",
                    content=event_marker
                ))
                brain_events.append(event_marker)
        
        # Determinar si fue exitoso
        success = result.get("success", False)
        
        if success:
            message = result.get("message", "Presentación generada")
            final_answer = f"✅ {message}"
            
            # Evento de confirmación
            events.append(self.create_token_event(f"\n{final_answer}\n"))
            
            return ToolResult(
                success=True,
                data=result,
                is_terminal=True,
                final_answer=final_answer,
                events=events,
                brain_events=brain_events,
                message_content=final_answer
            )
        else:
            error = result.get("error", "Error desconocido")
            return ToolResult(
                success=False,
                data=result,
                is_terminal=False,  # Permitir retry si falla
                events=events,
                message_content=f"Error generando presentación: {error}"
            )
