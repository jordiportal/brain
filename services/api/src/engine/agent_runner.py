"""
AgentRunner — Unified runner with task lifecycle, checkpointing, and memory.

Replaces the old ChainExecutor + AdaptiveExecutor pattern with a single
orchestration layer that:
  1. Manages Task lifecycle (submitted → working → completed/failed)
  2. Loads and saves memory (short/long/episodic)
  3. Wraps the existing builder pattern with checkpointing
  4. Supports resume from checkpoint (retry, input_required)
"""

import asyncio
import time
import uuid
import logging
from typing import AsyncGenerator, Optional

from .models import (
    Task,
    TaskState,
    Message,
    Part,
    Artifact,
    StreamEvent,
    ChainConfig,
    ChainInvokeRequest,
)
from .task_manager import TaskManager, task_manager
from .checkpoint import get_checkpointer
from .registry import chain_registry
from .chains.llm_utils import set_llm_execution_context, clear_llm_execution_context
from ..providers import get_active_llm_provider

logger = logging.getLogger(__name__)


class AgentRunner:
    """
    Unified runner that wraps the existing builder pattern with
    task lifecycle, checkpointing, and (future) memory integration.
    """

    def __init__(
        self,
        tm: Optional[TaskManager] = None,
        memory_manager=None,
    ):
        self._task_manager = tm or task_manager
        self._provider_loaded = False
        self._llm_provider_url: Optional[str] = None
        self._default_model: Optional[str] = None

        if memory_manager:
            self._memory_manager = memory_manager
        else:
            from .memory import MemoryManager
            self._memory_manager = MemoryManager()

    async def _ensure_provider_config(self):
        if not self._provider_loaded:
            provider = await get_active_llm_provider()
            if provider:
                self._llm_provider_url = provider.base_url
                self._default_model = provider.default_model
                self._provider_loaded = True

    def _get_default_url_for_provider(self, provider_type: str) -> str:
        import os
        default_urls = {
            "ollama": self._llm_provider_url or os.getenv("OLLAMA_BASE_URL", "http://192.168.7.101:11434"),
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com",
            "groq": "https://api.groq.com/openai/v1",
            "gemini": "https://generativelanguage.googleapis.com/v1beta",
            "azure": "https://api.openai.azure.com",
        }
        return default_urls.get(provider_type, self._llm_provider_url or "")

    async def run(
        self,
        task: Task,
        request: ChainInvokeRequest,
        session_id: Optional[str] = None,
    ) -> Task:
        """
        Execute a task synchronously (non-streaming).
        Returns the completed/failed task.
        """
        await self._ensure_provider_config()

        chain_id = task.chain_id or "adaptive"
        definition = chain_registry.get(chain_id)
        if not definition:
            await self._task_manager.fail(task.id, f"Chain not found: {chain_id}")
            return await self._task_manager.get(task.id)

        builder = chain_registry.get_builder(chain_id)
        if not builder:
            await self._task_manager.fail(task.id, f"Builder not found: {chain_id}")
            return await self._task_manager.get(task.id)

        await self._task_manager.start(task.id)
        start_time = time.perf_counter()
        execution_id = str(uuid.uuid4())
        set_llm_execution_context(execution_id, chain_id)

        try:
            llm_url = request.llm_provider_url or self._get_default_url_for_provider(request.llm_provider_type)
            model = request.model or definition.config.model or self._default_model or "qwen3:8b"

            chain_config = definition.config.model_copy()
            if request.config:
                for key, value in request.config.model_dump(exclude_unset=True).items():
                    if value is not None:
                        setattr(chain_config, key, value)

            memory = self._load_short_term_memory(session_id, chain_config)

            # Enrich with long-term + episodic memory context
            memory_addendum = await self._get_memory_addendum(
                user_id=task.created_by,
                agent_id=task.agent_id,
                context_id=session_id,
                task=task,
                query=request.input.get("message", request.input.get("query", "")),
            )

            result = None
            async for event in builder(
                config=chain_config,
                llm_url=llm_url,
                model=model,
                input_data=request.input,
                memory=memory,
                execution_id=execution_id,
                stream=False,
                provider_type=request.llm_provider_type,
                api_key=request.api_key,
                user_id=task.created_by,
                memory_addendum=memory_addendum,
            ):
                if isinstance(event, dict) and "_result" in event:
                    result = event["_result"]
                    break

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            response_text = ""
            iterations = 0
            tokens = 0

            if result:
                response_text = result.get("response", "")
                iterations = result.get("iterations", 0)

            output_msg = Message.text("agent", response_text)
            await self._task_manager.complete(task.id, output_msg)
            await self._task_manager.update_metrics(
                task.id, duration_ms=duration_ms, iterations=iterations, tokens_used=tokens,
            )

            # Post-completion: extract facts and create episodes
            await self._post_completion_memory(task)

        except Exception as e:
            logger.error(f"AgentRunner.run error: {e}", exc_info=True)
            await self._task_manager.fail(task.id, str(e))
        finally:
            clear_llm_execution_context()

        return await self._task_manager.get(task.id)

    async def run_stream(
        self,
        task: Task,
        request: ChainInvokeRequest,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Execute a task with streaming events.
        Yields StreamEvents and updates task lifecycle.
        """
        await self._ensure_provider_config()

        chain_id = task.chain_id or "adaptive"
        definition = chain_registry.get(chain_id)
        if not definition:
            await self._task_manager.fail(task.id, f"Chain not found: {chain_id}")
            yield StreamEvent(
                event_type="error",
                execution_id="",
                task_id=task.id,
                data={"error": f"Chain not found: {chain_id}"},
            )
            return

        builder = chain_registry.get_builder(chain_id)
        if not builder:
            await self._task_manager.fail(task.id, f"Builder not found: {chain_id}")
            yield StreamEvent(
                event_type="error",
                execution_id="",
                task_id=task.id,
                data={"error": f"Builder not found: {chain_id}"},
            )
            return

        await self._task_manager.start(task.id)
        start_time = time.perf_counter()
        execution_id = str(uuid.uuid4())
        set_llm_execution_context(execution_id, chain_id)

        full_response = ""
        iterations = 0

        try:
            llm_url = request.llm_provider_url or self._get_default_url_for_provider(request.llm_provider_type)
            model = request.model or definition.config.model or self._default_model or "qwen3:8b"

            chain_config = definition.config.model_copy()
            if request.config:
                for key, value in request.config.model_dump(exclude_unset=True).items():
                    if value is not None:
                        setattr(chain_config, key, value)

            memory = self._load_short_term_memory(session_id, chain_config)

            memory_addendum = await self._get_memory_addendum(
                user_id=task.created_by,
                agent_id=task.agent_id,
                context_id=session_id,
                task=task,
                query=request.input.get("message", request.input.get("query", "")),
            )

            yield StreamEvent(
                event_type="start",
                execution_id=execution_id,
                task_id=task.id,
                data={"chain_id": chain_id, "chain_name": definition.name},
            )

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
                user_id=task.created_by,
                memory_addendum=memory_addendum,
            ):
                if isinstance(event, dict):
                    if "_result" in event:
                        result = event["_result"]
                        iterations = result.get("iterations", 0)
                        continue
                    if "event_type" in event:
                        event = StreamEvent(**event)
                    else:
                        continue

                event.task_id = task.id
                yield event

                if event.event_type == "token" and event.content:
                    full_response += event.content

            duration_ms = int((time.perf_counter() - start_time) * 1000)
            output_msg = Message.text("agent", full_response) if full_response else None
            await self._task_manager.complete(task.id, output_msg)
            await self._task_manager.update_metrics(
                task.id,
                duration_ms=duration_ms,
                iterations=iterations,
            )

            await self._post_completion_memory(task)

            yield StreamEvent(
                event_type="end",
                execution_id=execution_id,
                task_id=task.id,
                data={"output": {"response": full_response}},
            )

        except Exception as e:
            logger.error(f"AgentRunner.run_stream error: {e}", exc_info=True)
            await self._task_manager.fail(task.id, str(e))
            yield StreamEvent(
                event_type="error",
                execution_id=execution_id,
                task_id=task.id,
                data={"error": str(e)},
            )
        finally:
            clear_llm_execution_context()

    async def resume(
        self,
        task: Task,
        input_message: Message,
        request: Optional[ChainInvokeRequest] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Resume a task from INPUT_REQUIRED or FAILED state.

        For INPUT_REQUIRED: provides user input and continues.
        For FAILED: retries from the last checkpoint.
        """
        if task.state == TaskState.INPUT_REQUIRED:
            await self._task_manager.provide_input(task.id, input_message)
        elif task.state == TaskState.FAILED:
            await self._task_manager.retry(task.id)
        else:
            yield StreamEvent(
                event_type="error",
                execution_id="",
                task_id=task.id,
                data={"error": f"Cannot resume task in {task.state.value} state"},
            )
            return

        checkpointer = get_checkpointer()
        if checkpointer and task.checkpoint_thread_id:
            logger.info(
                f"Resuming task {task.id} from checkpoint {task.checkpoint_thread_id}"
            )

        # Re-execute with updated input
        if not request:
            request = ChainInvokeRequest(
                input={"message": input_message.text_content},
            )

        async for event in self.run_stream(
            await self._task_manager.get(task.id),
            request,
            session_id=task.context_id,
        ):
            yield event

    async def cancel(self, task: Task) -> Task:
        """Cancel a running task."""
        return await self._task_manager.cancel(task.id, "Canceled by user")

    def _load_short_term_memory(
        self, session_id: Optional[str], config: ChainConfig
    ) -> list:
        if not config.use_memory or not session_id:
            return []

        from .executor import chain_executor
        return chain_executor.get_memory(session_id)

    async def _get_memory_addendum(
        self,
        user_id: Optional[str],
        agent_id: Optional[str],
        context_id: Optional[str],
        task: Optional[Task],
        query: Optional[str],
    ) -> str:
        """Build system prompt addendum from long-term + episodic memory."""
        if not user_id or not self._memory_manager:
            return ""
        try:
            ctx = await self._memory_manager.get_context(
                user_id=user_id,
                agent_id=agent_id,
                context_id=context_id,
                task=task,
                query=query,
            )
            return ctx.to_system_addendum()
        except Exception as e:
            logger.warning(f"Memory context retrieval failed: {e}")
            return ""

    async def _post_completion_memory(self, task: Task):
        """Post-completion: extract facts and create episodic summaries."""
        if not self._memory_manager or not task.created_by:
            return
        try:
            refreshed = await self._task_manager.get(task.id)
            if refreshed:
                from .memory import make_llm_call
                await self._memory_manager.save_interaction(refreshed, llm_call=make_llm_call())
        except Exception as e:
            logger.warning(f"Post-completion memory save failed: {e}")


# Global instance
agent_runner = AgentRunner()
