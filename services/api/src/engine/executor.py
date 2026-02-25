"""
Ejecutor de cadenas y grafos
"""

import json
import uuid
import asyncio
import time
from datetime import datetime
from typing import AsyncGenerator, Optional, Any, Dict
import httpx
import structlog
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .models import (
    ChainDefinition,
    ChainConfig,
    ExecutionState,
    ExecutionResult,
    ExecutionStep,
    ExecutionStatus,
    StreamEvent,
    ChainInvokeRequest
)
from .registry import chain_registry
from src.providers import get_active_llm_provider

logger = structlog.get_logger()


# ============================================
# Monitoring Helper
# ============================================

async def _trace_execution(
    execution_id: str,
    chain_id: str,
    event_type: str,
    duration_ms: float = None,
    success: bool = None,
    error_message: str = None,
    metadata: dict = None
):
    """Helper para registrar trazas de ejecución"""
    try:
        from src.monitoring import monitoring_service
        
        if event_type == "chain_start":
            await monitoring_service.trace_start(
                execution_id=execution_id,
                chain_id=chain_id,
                metadata=metadata
            )
        elif event_type == "chain_end":
            await monitoring_service.trace_end(
                execution_id=execution_id,
                chain_id=chain_id,
                duration_ms=duration_ms,
                success=success,
                error_message=error_message,
                metadata=metadata
            )
    except Exception as e:
        # No fallar si hay error en monitorización
        logger.warning(f"Error tracing execution: {e}")


class ChainExecutor:
    """Ejecutor principal de cadenas"""
    
    def __init__(
        self,
        llm_provider_url: str = None,
        default_model: str = None
    ):
        # Se configura dinámicamente desde Strapi
        self._llm_provider_url = llm_provider_url
        self._default_model = default_model
        self._memory_store: Dict[str, list] = {}  # Memoria por sesión
        self._provider_loaded = False
    
    @property
    def llm_provider_url(self) -> str:
        import os
        return self._llm_provider_url or os.getenv("OLLAMA_BASE_URL", "http://192.168.7.101:11434")
    
    @llm_provider_url.setter
    def llm_provider_url(self, value: str):
        self._llm_provider_url = value
    
    @property
    def default_model(self) -> str:
        return self._default_model or "qwen3:8b"
    
    @default_model.setter
    def default_model(self, value: str):
        self._default_model = value
    
    async def _ensure_provider_config(self):
        """Cargar configuración del provider desde Strapi si no está cargada"""
        if not self._provider_loaded:
            provider = await get_active_llm_provider()
            if provider:
                self._llm_provider_url = provider.base_url
                self._default_model = provider.default_model
                self._provider_loaded = True
    
    def _get_default_url_for_provider(self, provider_type: str) -> str:
        """Obtener URL por defecto según el tipo de proveedor"""
        default_urls = {
            "ollama": self.llm_provider_url,  # URL de Ollama configurada
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com",
            "groq": "https://api.groq.com/openai/v1",
            "gemini": "https://generativelanguage.googleapis.com/v1beta",
            "azure": "https://api.openai.azure.com"
        }
        return default_urls.get(provider_type, self.llm_provider_url)
    
    async def invoke(
        self,
        chain_id: str,
        request: ChainInvokeRequest,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> ExecutionResult:
        """Ejecutar una cadena y devolver el resultado"""
        
        # Cargar configuración de Strapi
        await self._ensure_provider_config()
        
        # Obtener definición y builder
        definition = chain_registry.get(chain_id)
        if not definition:
            raise ValueError(f"Cadena no encontrada: {chain_id}")
        
        builder = chain_registry.get_builder(chain_id)
        if not builder:
            raise ValueError(f"Builder no encontrado para: {chain_id}")
        
        # Crear estado de ejecución
        execution_state = ExecutionState(
            chain_id=chain_id,
            chain_name=definition.name,
            input_data=request.input,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        
        # Trazar inicio de ejecución
        start_time = time.perf_counter()
        asyncio.create_task(_trace_execution(
            execution_id=execution_state.execution_id,
            chain_id=chain_id,
            event_type="chain_start",
            metadata={"model": request.model, "provider": request.llm_provider_type}
        ))
        
        try:
            # Configurar LLM según proveedor
            llm_url = request.llm_provider_url
            if not llm_url:
                # Usar URL por defecto según el tipo de proveedor
                llm_url = self._get_default_url_for_provider(request.llm_provider_type)
            model = request.model or definition.config.model or self.default_model
            
            # Merge config: request config sobrescribe definition config
            chain_config = definition.config.model_copy()
            if request.config:
                # Actualizar con valores del request que no sean None
                for key, value in request.config.model_dump(exclude_unset=True).items():
                    if value is not None:
                        setattr(chain_config, key, value)
            
            # Obtener memoria si está habilitada
            memory = []
            if chain_config.use_memory and session_id:
                memory = self._memory_store.get(session_id, [])
            
            # Construir y ejecutar el grafo
            result = None
            async for event in builder(
                config=chain_config,
                llm_url=llm_url,
                model=model,
                input_data=request.input,
                memory=memory,
                execution_state=execution_state,
                stream=False,
                provider_type=request.llm_provider_type,
                api_key=request.api_key,
                user_id=user_id,
            ):
                # El resultado viene como un dict con _result
                if isinstance(event, dict) and "_result" in event:
                    result = event["_result"]
                    break
            
            # Actualizar memoria
            if definition.config.use_memory and session_id:
                self._update_memory(
                    session_id,
                    request.input,
                    result,
                    definition.config.max_memory_messages
                )
            
            # Completar ejecución
            execution_state.status = ExecutionStatus.COMPLETED
            execution_state.output_data = result
            execution_state.completed_at = datetime.utcnow()
            
            if execution_state.started_at:
                execution_state.total_duration_ms = int(
                    (execution_state.completed_at - execution_state.started_at).total_seconds() * 1000
                )
            
            # Trazar fin exitoso
            duration_ms = (time.perf_counter() - start_time) * 1000
            asyncio.create_task(_trace_execution(
                execution_id=execution_state.execution_id,
                chain_id=chain_id,
                event_type="chain_end",
                duration_ms=duration_ms,
                success=True
            ))
            
        except Exception as e:
            logger.error(f"Error ejecutando cadena: {e}", chain_id=chain_id)
            execution_state.status = ExecutionStatus.FAILED
            execution_state.error = str(e)
            execution_state.completed_at = datetime.utcnow()
            
            # Trazar error
            duration_ms = (time.perf_counter() - start_time) * 1000
            asyncio.create_task(_trace_execution(
                execution_id=execution_state.execution_id,
                chain_id=chain_id,
                event_type="chain_end",
                duration_ms=duration_ms,
                success=False,
                error_message=str(e)
            ))
        
        return ExecutionResult(
            execution_id=execution_state.execution_id,
            chain_id=chain_id,
            status=execution_state.status,
            input_data=execution_state.input_data,
            output_data=execution_state.output_data,
            steps=execution_state.steps,
            total_tokens=execution_state.total_tokens,
            total_duration_ms=execution_state.total_duration_ms,
            error=execution_state.error
        )
    
    async def invoke_stream(
        self,
        chain_id: str,
        request: ChainInvokeRequest,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Ejecutar una cadena con streaming de eventos"""
        
        # Cargar configuración de Strapi
        await self._ensure_provider_config()
        
        definition = chain_registry.get(chain_id)
        if not definition:
            yield StreamEvent(
                event_type="error",
                execution_id="",
                data={"error": f"Cadena no encontrada: {chain_id}"}
            )
            return
        
        builder = chain_registry.get_builder(chain_id)
        if not builder:
            yield StreamEvent(
                event_type="error",
                execution_id="",
                data={"error": f"Builder no encontrado para: {chain_id}"}
            )
            return
        
        execution_id = str(uuid.uuid4())
        start_time = time.perf_counter()
        
        # Trazar inicio de ejecución
        asyncio.create_task(_trace_execution(
            execution_id=execution_id,
            chain_id=chain_id,
            event_type="chain_start",
            metadata={"model": request.model, "provider": request.llm_provider_type, "stream": True}
        ))
        
        # Evento de inicio
        yield StreamEvent(
            event_type="start",
            execution_id=execution_id,
            data={
                "chain_id": chain_id,
                "chain_name": definition.name,
                "input": request.input
            }
        )
        
        try:
            # Configurar LLM según proveedor
            llm_url = request.llm_provider_url
            if not llm_url:
                llm_url = self._get_default_url_for_provider(request.llm_provider_type)
            model = request.model or definition.config.model or self.default_model
            
            # Merge config: request config sobrescribe definition config
            chain_config = definition.config.model_copy()
            if request.config:
                for key, value in request.config.model_dump(exclude_unset=True).items():
                    if value is not None:
                        setattr(chain_config, key, value)
            
            memory = []
            if chain_config.use_memory and session_id:
                memory = self._memory_store.get(session_id, [])
            
            # Ejecutar con streaming
            full_response = ""
            async for event in builder(
                config=chain_config,
                llm_url=llm_url,
                model=model,
                input_data=request.input,
                memory=memory,
                execution_id=execution_id,
                stream=True,
                provider_type=request.llm_provider_type,
                api_key=request.api_key,
                emit_brain_events=request.emit_brain_events,
                user_id=user_id,
            ):
                # El builder puede devolver StreamEvent o dict
                if isinstance(event, dict):
                    # Es un dict puro (como _result al final)
                    if "_result" in event:
                        # Resultado final, no emitir al stream
                        continue
                    # Convertir dict a StreamEvent si tiene los campos necesarios
                    if "event_type" in event:
                        event = StreamEvent(**event)
                    else:
                        continue
                
                yield event
                if hasattr(event, 'event_type') and event.event_type == "token" and event.content:
                    full_response += event.content
            
            # Actualizar memoria
            if chain_config.use_memory and session_id and full_response:
                self._update_memory(
                    session_id,
                    request.input,
                    {"response": full_response},
                    chain_config.max_memory_messages
                )
            
            # Trazar fin exitoso
            duration_ms = (time.perf_counter() - start_time) * 1000
            asyncio.create_task(_trace_execution(
                execution_id=execution_id,
                chain_id=chain_id,
                event_type="chain_end",
                duration_ms=duration_ms,
                success=True
            ))
            
            # Evento de fin
            yield StreamEvent(
                event_type="end",
                execution_id=execution_id,
                data={"output": {"response": full_response}}
            )
            
        except Exception as e:
            logger.error(f"Error en streaming: {e}", chain_id=chain_id)
            
            # Trazar error
            duration_ms = (time.perf_counter() - start_time) * 1000
            asyncio.create_task(_trace_execution(
                execution_id=execution_id,
                chain_id=chain_id,
                event_type="chain_end",
                duration_ms=duration_ms,
                success=False,
                error_message=str(e)
            ))
            
            yield StreamEvent(
                event_type="error",
                execution_id=execution_id,
                data={"error": str(e)}
            )
    
    def _update_memory(
        self,
        session_id: str,
        input_data: dict,
        output_data: dict,
        max_messages: int
    ):
        """Actualizar memoria de la sesión"""
        if session_id not in self._memory_store:
            self._memory_store[session_id] = []
        
        # Añadir mensajes
        user_msg = input_data.get("message") or input_data.get("query") or str(input_data)
        assistant_msg = output_data.get("response") or output_data.get("answer") or str(output_data)
        
        self._memory_store[session_id].append({
            "role": "user",
            "content": user_msg
        })
        self._memory_store[session_id].append({
            "role": "assistant", 
            "content": assistant_msg
        })
        
        # Limitar memoria
        if len(self._memory_store[session_id]) > max_messages * 2:
            self._memory_store[session_id] = self._memory_store[session_id][-max_messages * 2:]
    
    def clear_memory(self, session_id: str):
        """Limpiar memoria de una sesión"""
        if session_id in self._memory_store:
            del self._memory_store[session_id]
    
    def get_memory(self, session_id: str) -> list:
        """Obtener memoria de una sesión"""
        return self._memory_store.get(session_id, [])


# Instancia global del ejecutor
chain_executor = ChainExecutor()
