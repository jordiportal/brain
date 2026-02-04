"""
AdaptiveExecutor - Loop principal del Adaptive Agent.

Este es el núcleo simplificado que orquesta:
1. Llamadas al LLM
2. Ejecución de tools via handlers
3. Emisión de eventos
4. Control de flujo (loops, límites, finalización)
"""

import json
from typing import AsyncGenerator, Optional, Any

import structlog

from ...models import StreamEvent, ChainConfig
from ...reasoning import ComplexityAnalysis
from ...reasoning.modes import ReasoningConfig
from ....tools import tool_registry
from ..llm_utils import call_llm_with_tools, LLMToolResponse

from .validators import is_valid_tool_name, LoopDetector, validate_json_args
from .handlers import get_handler, HANDLER_REGISTRY
from .handlers.base import DefaultHandler, ToolResult
from .events import StreamEmitter, BrainEmitter


logger = structlog.get_logger()


class AdaptiveExecutor:
    """
    Executor del Adaptive Agent.
    
    Orquesta el loop principal de ejecución manteniendo el código
    limpio y delegando responsabilidades a handlers y emitters.
    """
    
    # Nombres amigables para tools sin handler específico
    TOOL_DISPLAY_NAMES = {
        "read_file": "📖 Leyendo archivo",
        "write_file": "✍️ Escribiendo archivo",
        "edit_file": "✏️ Editando archivo",
        "list_directory": "📁 Listando directorio",
        "search_files": "🔎 Buscando en archivos",
        "shell": "💻 Ejecutando comando",
        "python": "🐍 Ejecutando Python",
        "javascript": "📜 Ejecutando JavaScript",
        "web_search": "🌐 Buscando en web",
        "web_fetch": "📥 Obteniendo URL",
        "calculate": "🔢 Calculando",
        "think": "💭 Pensando",
        "reflect": "🔍 Reflexionando",
        "plan": "📋 Planificando",
        "delegate": "🤖 Delegando a subagente",
        "consult_team_member": "👥 Consultando miembro del equipo",
        "finish": "✅ Finalizando",
        # generate_slides movido a slides_agent - usar delegate
    }
    
    def __init__(
        self,
        execution_id: str,
        llm_url: str,
        model: str,
        provider_type: str,
        api_key: Optional[str],
        complexity: ComplexityAnalysis,
        reasoning_config: ReasoningConfig,
        chain_config: ChainConfig,
        emit_brain_events: bool = False,
        is_continue_request: bool = False
    ):
        self.execution_id = execution_id
        self.llm_url = llm_url
        self.model = model
        self.provider_type = provider_type
        self.api_key = api_key
        self.complexity = complexity
        self.reasoning_config = reasoning_config
        self.chain_config = chain_config
        self.emit_brain_events = emit_brain_events
        self.is_continue_request = is_continue_request
        
        # Configurar límite de iteraciones
        base_max = (
            chain_config.max_iterations 
            if hasattr(chain_config, 'max_iterations') and chain_config.max_iterations 
            else reasoning_config.max_iterations
        )
        self.max_iterations = base_max * 2 if is_continue_request else base_max
        self.ask_before_continue = getattr(chain_config, 'ask_before_continue', True)
        
        # Estado de ejecución
        self.iteration = 0
        self.tool_results: list[dict] = []
        self.final_answer: Optional[str] = None
        self.execution_complete = False
        
        # Detectores y emitters
        self.loop_detector = LoopDetector(max_consecutive=3)
        self.stream_emitter = StreamEmitter(execution_id)
        self.brain_emitter = BrainEmitter(execution_id, enabled=emit_brain_events)
        
        # Config LLM para handlers
        self.llm_config = {
            "url": llm_url,
            "model": model,
            "provider": provider_type,
            "api_key": api_key
        }
    
    def _get_display_name(self, tool_name: str) -> str:
        """Obtiene nombre amigable para una tool."""
        return self.TOOL_DISPLAY_NAMES.get(tool_name, f"🔧 {tool_name}")
    
    def _get_handler(self, tool_name: str):
        """
        Obtiene el handler apropiado para una tool.
        
        Usa handler específico si existe, sino DefaultHandler.
        """
        handler_class = get_handler(tool_name)
        
        kwargs = {
            "execution_id": self.execution_id,
            "iteration": self.iteration,
            "emit_brain_events": self.emit_brain_events,
            "llm_config": self.llm_config
        }
        
        if handler_class:
            # Handler específico (algunos necesitan tool_name)
            if tool_name in ("think", "reflect", "plan"):
                return handler_class(tool_name=tool_name, **kwargs)
            return handler_class(**kwargs)
        else:
            # Handler por defecto
            return DefaultHandler(tool_name=tool_name, **kwargs)
    
    async def execute(
        self,
        messages: list[dict],
        tools: list[dict]
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Loop principal de ejecución.
        
        Args:
            messages: Lista de mensajes (system, user, etc.)
            tools: Lista de tools en formato LLM
            
        Yields:
            StreamEvents durante la ejecución
        """
        while self.iteration < self.max_iterations and not self.execution_complete:
            self.iteration += 1
            
            # Evento de inicio de iteración
            yield self.stream_emitter.iteration_start(self.iteration, self.max_iterations)
            
            try:
                # Llamar al LLM
                response = await call_llm_with_tools(
                    llm_url=self.llm_url,
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    temperature=self.reasoning_config.temperature,
                    provider_type=self.provider_type,
                    api_key=self.api_key
                )
                
                # Procesar respuesta
                async for event in self._process_response(response, messages, tools):
                    yield event
                
                # Si hay respuesta final, terminar
                if self.final_answer is not None:
                    yield self.stream_emitter.node_end(
                        f"iteration_{self.iteration}",
                        {"finished": True}
                    )
                    break
                
                # Inyectar warning si hay loop
                if self.loop_detector.consecutive_count >= 3:
                    messages.append({
                        "role": "system",
                        "content": self.loop_detector.get_warning_message()
                    })
                    logger.info(
                        "⚠️ Loop warning injected",
                        tool=self.loop_detector.last_tool_name,
                        count=self.loop_detector.consecutive_count
                    )
                
                yield self.stream_emitter.iteration_end(
                    self.iteration,
                    tools_used=len(response.tool_calls) if response.tool_calls else 0
                )
                
            except Exception as e:
                logger.error(f"Error in iteration {self.iteration}: {e}", exc_info=True)
                yield self.stream_emitter.error(str(e), f"iteration_{self.iteration}")
                continue
    
    def _extract_answer(self, content: str) -> str:
        """
        Extrae el campo 'answer' de un JSON si es posible.
        
        El LLM a veces responde con formato JSON como:
        {"answer": "...", "confidence": 1.0}
        
        Esta función extrae solo el campo 'answer'.
        """
        if not content:
            return content
            
        content = content.strip()
        
        # Intentar parsear como JSON
        if content.startswith("{") and content.endswith("}"):
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    # Buscar campo answer o final_answer
                    answer = data.get("answer") or data.get("final_answer")
                    if answer:
                        return answer
            except json.JSONDecodeError:
                pass
        
        return content
    
    async def _process_response(
        self,
        response: LLMToolResponse,
        messages: list[dict],
        tools: list[dict]
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Procesa la respuesta del LLM.
        
        Maneja dos casos:
        1. Respuesta directa (sin tool calls)
        2. Tool calls
        """
        # Caso 1: Respuesta directa
        if response.content and not response.tool_calls:
            logger.info(f"📝 Direct response (iteration {self.iteration})")
            
            # Extraer answer si es JSON
            answer = self._extract_answer(response.content)
            self.final_answer = answer
            yield self.stream_emitter.token(answer)
            yield self.stream_emitter.node_end(
                f"iteration_{self.iteration}",
                {"direct_response": True}
            )
            return
        
        # Caso 2: Tool calls
        if response.tool_calls:
            # Agregar mensaje del assistant
            if self.provider_type != "ollama":
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.get("name"),
                            "arguments": tc.function.get("arguments", "{}")
                        }
                    } for tc in response.tool_calls]
                })
            
            # Nombres de tools disponibles en este contexto (LLM puede llamar cualquiera de estas)
            available_tool_names = {
                t.get("function", {}).get("name", "")
                for t in tools
                if isinstance(t, dict) and t.get("type") == "function"
            }
            # Ejecutar cada tool
            for tool_call in response.tool_calls:
                async for event in self._execute_tool(tool_call, messages, available_tool_names):
                    yield event
                
                # Si terminamos, salir del loop de tools
                if self.execution_complete or self.final_answer is not None:
                    break
    
    async def _execute_tool(
        self,
        tool_call: Any,
        messages: list[dict],
        available_tool_names: Optional[set] = None
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Ejecuta una tool individual.
        """
        tool_name = tool_call.function.get("name", "")
        
        # Validar: válida si está en VALID_TOOL_NAMES O si está en las tools ofrecidas al LLM
        is_valid = is_valid_tool_name(tool_name) or (
            available_tool_names and tool_name in available_tool_names
        )
        if not is_valid:
            logger.warning(f"⚠️ Invalid tool ignored: {tool_name}")
            error_msg = json.dumps({
                "error": f"Tool '{tool_name}' is not available or invalid",
                "success": False
            }, ensure_ascii=False)
            if self.provider_type == "ollama":
                messages.append({"role": "tool", "content": error_msg})
            else:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": error_msg
                })
            return
        
        # Parsear argumentos
        args_str = tool_call.function.get("arguments", "{}")
        args = validate_json_args(args_str)
        
        logger.info(f"🔧 Executing: {tool_name}", args=list(args.keys()))
        
        # Detectar loops
        loop_detected = self.loop_detector.track(tool_name)
        if loop_detected:
            logger.warning(
                f"⚠️ Loop detected: {tool_name} x{self.loop_detector.consecutive_count}"
            )
        
        # Obtener handler
        handler = self._get_handler(tool_name)
        
        # Evento de inicio
        yield self.stream_emitter.tool_start(
            tool_name,
            handler.display_name or self._get_display_name(tool_name),
            self.iteration,
            args
        )
        
        # Brain Event de action start
        brain_event = self.brain_emitter.action_start(tool_name, args)
        if brain_event:
            yield brain_event
        
        # Preparar argumentos
        exec_args = handler.prepare_args(args)
        
        # Ejecutar tool
        raw_result = await tool_registry.execute(tool_name, **exec_args)
        
        # Procesar resultado con handler
        result = await handler.process_result(raw_result, args)
        
        # Emitir eventos del handler
        for event in result.events:
            yield event
        
        # Brain Events post-tool
        results_count = self.brain_emitter.get_results_count(tool_name, raw_result)
        brain_event = self.brain_emitter.action_complete(tool_name, args, results_count)
        if brain_event:
            yield brain_event
        
        # Sources para web_search
        if tool_name == "web_search" and isinstance(raw_result, dict):
            sources_event = self.brain_emitter.sources_from_web_search(raw_result)
            if sources_event:
                yield sources_event
        
        # Guardar resultado
        self.tool_results.append({
            "tool": tool_name,
            "result": raw_result
        })
        
        # Actualizar estado si es terminal
        if result.is_terminal:
            self.execution_complete = True
            self.final_answer = result.final_answer
        
        # Evento de fin de tool (incluir html si es presentación)
        # Usar message_content completo como "conversation" para la UI
        conversation = result.message_content or ""
        html = raw_result.get("data", {}).get("html") if isinstance(raw_result, dict) else None
        yield self.stream_emitter.tool_end(
            tool_name,
            self.iteration,
            success=result.success,
            preview=conversation[:200] if conversation else "",
            thinking=result.data.get("thinking"),
            done=result.is_terminal,
            html=html,
            conversation=conversation  # Contenido completo para la UI
        )
        
        # Agregar resultado a mensajes
        result_str = json.dumps(raw_result, ensure_ascii=False, default=str)
        if len(result_str) > 16000:
            result_str = result_str[:16000] + "... [truncated]"
        
        if self.provider_type == "ollama":
            messages.append({
                "role": "tool",
                "content": result_str
            })
        else:
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_name,
                "content": result_str
            })
    
    async def force_finish(
        self,
        messages: list[dict],
        tools: list[dict]
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Fuerza una respuesta final del LLM cuando no llamó finish.
        """
        tools_summary = ", ".join([tr["tool"] for tr in self.tool_results]) or "ninguna"
        
        force_prompt = f"""You have completed {self.iteration} iterations using these tools: {tools_summary}.

Now you MUST provide your final answer using the `finish` tool. Summarize what was accomplished and provide the answer to the user's original request.

IMPORTANT: You MUST call the `finish` tool now with your complete answer."""
        
        messages.append({"role": "user", "content": force_prompt})
        
        try:
            response = await call_llm_with_tools(
                llm_url=self.llm_url,
                model=self.model,
                messages=messages,
                tools=tools,
                temperature=0.3,
                provider_type=self.provider_type,
                api_key=self.api_key
            )
            
            # Buscar finish en tool_calls
            if response.tool_calls:
                for tc in response.tool_calls:
                    if tc.function.get("name") == "finish":
                        try:
                            args = json.loads(tc.function.get("arguments", "{}"))
                            self.final_answer = args.get("answer") or args.get("final_answer", "")
                        except:
                            self.final_answer = tc.function.get("arguments", "")
                        break
            
            # Usar content si no hay finish
            if not self.final_answer and response.content:
                self.final_answer = self._extract_answer(response.content)
                
        except Exception as e:
            logger.error(f"Error forcing finish: {e}")
        
        # Fallback si aún no hay respuesta
        if not self.final_answer:
            if self.tool_results:
                last_results = self.tool_results[-3:]
                summaries = []
                for tr in last_results:
                    result = tr.get("result", {})
                    if isinstance(result, dict):
                        content = result.get("content") or result.get("data")
                        if content:
                            summaries.append(str(content)[:500])
                
                if summaries:
                    self.final_answer = "Resultados obtenidos:\n\n" + "\n\n".join(summaries)
                else:
                    self.final_answer = f"Tarea procesada usando: {tools_summary}. Consulta los archivos generados para ver los resultados."
            else:
                self.final_answer = "No se pudo completar la tarea. Por favor, reformula tu petición."
        
        yield self.stream_emitter.token(self.final_answer)
    
    def get_iteration_limit_message(self) -> str:
        """Genera mensaje cuando se alcanza el límite de iteraciones."""
        tools_summary = ", ".join([tr["tool"] for tr in self.tool_results]) or "ninguna"
        
        return f"""He llegado al límite de {self.max_iterations} iteraciones configurado.

**Progreso actual:**
- Iteraciones usadas: {self.iteration}
- Herramientas utilizadas: {tools_summary}
- Tareas completadas: {len(self.tool_results)} acciones

¿Quieres que continúe trabajando en la tarea? Responde **"continúa"** para seguir o **"finaliza"** para obtener un resumen de lo realizado."""
