"""
Handler para la tool `delegate`.

Maneja delegación a subagentes especializados:
- media_agent: Generación de imágenes
- slides_agent: Generación de presentaciones (legacy, usar generate_slides)
"""

from .base import ToolHandler, ToolResult
from ....models import StreamEvent


class DelegateHandler(ToolHandler):
    """
    Handler para delegación a subagentes.
    """
    
    tool_name = "delegate"
    display_name = "🤖 Delegando a subagente"
    is_terminal = False  # Por defecto no es terminal
    
    def prepare_args(self, args: dict) -> dict:
        """Inyecta configuración LLM para el subagente."""
        prepared = args.copy()
        
        # Inyectar config LLM si está disponible
        if self.llm_config:
            prepared["_llm_url"] = self.llm_config.get("url")
            prepared["_model"] = self.llm_config.get("model")
            prepared["_provider_type"] = self.llm_config.get("provider")
            prepared["_api_key"] = self.llm_config.get("api_key")
        
        return prepared
    
    async def process_result(self, result: dict, args: dict) -> ToolResult:
        """
        Procesa el resultado de delegación.
        
        Maneja casos especiales:
        - Imágenes de media_agent
        - Brain Events de slides_agent
        """
        events = []
        brain_events = []
        is_terminal = False
        final_answer = None
        
        if not result.get("success"):
            return ToolResult(
                success=False,
                data=result,
                message_content=f"Error en delegación: {result.get('error', 'Unknown')}"
            )
        
        agent_name = args.get("agent", "unknown")
        
        # Manejar imágenes de media_agent / designer_agent
        if result.get("images"):
            for img in result["images"]:
                if img.get("url"):
                    events.append(StreamEvent(
                        event_type="image",
                        execution_id=self.execution_id,
                        node_id=f"tool_{self.tool_name}_{self.iteration}",
                        data={
                            "image_url": img["url"],
                            "alt_text": img.get("prompt", "Generated image"),
                            "provider": img.get("provider"),
                            "model": img.get("model")
                        }
                    ))
                elif img.get("base64"):
                    events.append(StreamEvent(
                        event_type="image",
                        execution_id=self.execution_id,
                        node_id=f"tool_{self.tool_name}_{self.iteration}",
                        data={
                            "image_data": img["base64"],
                            "mime_type": img.get("mime_type", "image/png"),
                            "alt_text": img.get("prompt", "Generated image")
                        }
                    ))
            
            # Si hay imágenes, es terminal - la tarea está completa
            is_terminal = True
            num_images = len(result["images"])
            final_answer = result.get("response", f"He generado {num_images} imagen(es).")
        
        # Manejar vídeos generados
        if result.get("videos"):
            for vid in result["videos"]:
                if vid.get("url"):
                    events.append(StreamEvent(
                        event_type="video",
                        execution_id=self.execution_id,
                        node_id=f"tool_{self.tool_name}_{self.iteration}",
                        data={
                            "video_url": vid["url"],
                            "duration_seconds": vid.get("duration_seconds"),
                            "resolution": vid.get("resolution"),
                            "provider": vid.get("provider"),
                            "model": vid.get("model")
                        }
                    ))
                elif vid.get("base64"):
                    events.append(StreamEvent(
                        event_type="video",
                        execution_id=self.execution_id,
                        node_id=f"tool_{self.tool_name}_{self.iteration}",
                        data={
                            "video_data": vid["base64"],
                            "mime_type": vid.get("mime_type", "video/mp4"),
                            "duration_seconds": vid.get("duration_seconds"),
                            "resolution": vid.get("resolution")
                        }
                    ))
            
            # Si hay vídeos, es terminal - la tarea está completa
            is_terminal = True
            num_videos = len(result["videos"])
            final_answer = result.get("response", f"He generado {num_videos} vídeo(s).")
        
        # Manejar Brain Events de slides_agent (legacy)
        response_text = result.get("response", "")
        if "<!--BRAIN_EVENT:" in response_text:
            # Emitir directamente al stream
            events.append(self.create_token_event(
                response_text,
                node_id=f"subagent_{result.get('agent_id', agent_name)}"
            ))
            
            # Es terminal si contiene presentación
            is_terminal = True
            title = result.get("data", {}).get("title", "Sin título")
            slides_count = result.get("data", {}).get("slides_count", "?")
            final_answer = f"Presentación generada: {title} ({slides_count} slides)"
            
            events.append(self.create_token_event(final_answer))
        
        return ToolResult(
            success=True,
            data=result,
            is_terminal=is_terminal,
            final_answer=final_answer,
            events=events,
            brain_events=brain_events,
            message_content=response_text or str(result)[:16000]
        )
