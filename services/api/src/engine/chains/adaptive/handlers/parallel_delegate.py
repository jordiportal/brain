"""
Handler para la tool `parallel_delegate`.

Maneja delegación paralela a múltiples subagentes:
- Inyecta configuración LLM y execution_id
- Procesa resultados agregados (imágenes, vídeos, respuestas)
- Emite eventos por cada subagente hijo
"""

from .base import ToolHandler, ToolResult
from ....models import StreamEvent


class ParallelDelegateHandler(ToolHandler):
    """
    Handler para delegación paralela a subagentes.
    
    Procesa el resultado agregado de múltiples ejecuciones
    concurrentes, emitiendo eventos para cada subagente.
    """
    
    tool_name = "parallel_delegate"
    display_name = "🔀 Delegación paralela"
    is_terminal = False
    
    def prepare_args(self, args: dict) -> dict:
        """Inyecta configuración LLM y execution_id para las ejecuciones hijas."""
        prepared = args.copy()
        
        if self.llm_config:
            prepared["_llm_url"] = self.llm_config.get("url")
            prepared["_model"] = self.llm_config.get("model")
            prepared["_provider_type"] = self.llm_config.get("provider")
            prepared["_api_key"] = self.llm_config.get("api_key")
        
        prepared["_execution_id"] = self.execution_id
        
        return prepared
    
    async def process_result(self, result: dict, args: dict) -> ToolResult:
        """
        Procesa el resultado agregado de la delegación paralela.
        
        Recorre cada resultado hijo y emite eventos de imagen/vídeo
        si corresponde, igual que DelegateHandler pero para N resultados.
        """
        events = []
        is_terminal = False
        final_answer = None
        
        if not result.get("success"):
            return ToolResult(
                success=False,
                data=result,
                message_content=f"Error en delegación paralela: {result.get('error', 'Unknown')}"
            )
        
        results_list = result.get("results", [])
        summary = result.get("summary", {})
        
        all_responses = []
        has_media = False
        
        for child_result in results_list:
            agent_id = child_result.get("agent_id", "unknown")
            agent_name = child_result.get("agent_name", agent_id)
            
            if not child_result.get("success"):
                all_responses.append(
                    f"**{agent_name}** (error): {child_result.get('error', 'Error desconocido')}"
                )
                continue
            
            # Recopilar respuesta
            response_text = child_result.get("response", "")
            all_responses.append(f"**{agent_name}**: {response_text}")
            
            # Emitir eventos de imágenes
            if child_result.get("images"):
                has_media = True
                for img in child_result["images"]:
                    if img.get("url"):
                        events.append(StreamEvent(
                            event_type="image",
                            execution_id=self.execution_id,
                            node_id=f"parallel_{agent_id}_{self.iteration}",
                            data={
                                "image_url": img["url"],
                                "alt_text": img.get("prompt", "Generated image"),
                                "provider": img.get("provider"),
                                "model": img.get("model"),
                                "agent_id": agent_id
                            }
                        ))
                    elif img.get("base64"):
                        events.append(StreamEvent(
                            event_type="image",
                            execution_id=self.execution_id,
                            node_id=f"parallel_{agent_id}_{self.iteration}",
                            data={
                                "image_data": img["base64"],
                                "mime_type": img.get("mime_type", "image/png"),
                                "alt_text": img.get("prompt", "Generated image"),
                                "agent_id": agent_id
                            }
                        ))
            
            # Emitir eventos de vídeos
            if child_result.get("videos"):
                has_media = True
                for vid in child_result["videos"]:
                    if vid.get("url"):
                        events.append(StreamEvent(
                            event_type="video",
                            execution_id=self.execution_id,
                            node_id=f"parallel_{agent_id}_{self.iteration}",
                            data={
                                "video_url": vid["url"],
                                "duration_seconds": vid.get("duration_seconds"),
                                "resolution": vid.get("resolution"),
                                "provider": vid.get("provider"),
                                "model": vid.get("model"),
                                "agent_id": agent_id
                            }
                        ))
                    elif vid.get("base64"):
                        events.append(StreamEvent(
                            event_type="video",
                            execution_id=self.execution_id,
                            node_id=f"parallel_{agent_id}_{self.iteration}",
                            data={
                                "video_data": vid["base64"],
                                "mime_type": vid.get("mime_type", "video/mp4"),
                                "duration_seconds": vid.get("duration_seconds"),
                                "resolution": vid.get("resolution"),
                                "agent_id": agent_id
                            }
                        ))
            
            # Brain Events de slides (legacy)
            if "<!--BRAIN_EVENT:" in response_text:
                events.append(self.create_token_event(
                    response_text,
                    node_id=f"parallel_{agent_id}"
                ))
                has_media = True
        
        # Si hay media, es terminal
        if has_media:
            is_terminal = True
            final_answer = "\n\n".join(all_responses)
        
        # Construir contenido del mensaje con resumen
        successes = summary.get("successes", 0)
        failures = summary.get("failures", 0)
        total_time = summary.get("total_execution_time_ms", 0)
        agents_used = summary.get("agents_used", [])
        
        message_parts = [
            f"Delegación paralela completada ({successes} éxitos, {failures} fallos, {total_time}ms)",
            f"Agentes: {', '.join(agents_used)}",
            "",
            *all_responses
        ]
        message_content = "\n".join(message_parts)
        
        return ToolResult(
            success=True,
            data=result,
            is_terminal=is_terminal,
            final_answer=final_answer,
            events=events,
            message_content=message_content
        )
