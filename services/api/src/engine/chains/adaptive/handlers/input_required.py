"""
InputRequiredHandler — Pauses execution to request user input.

When an agent calls `request_input`, the task transitions to
INPUT_REQUIRED state. The user can then provide input via the
/tasks/{id}/resume endpoint, and execution continues.
"""

from typing import Any
from .base import ToolHandler, ToolResult
from ....models import StreamEvent


class InputRequiredHandler(ToolHandler):
    """
    Handler for the request_input tool.
    Marks execution as terminal (paused) and emits an input_required event.
    """

    @property
    def display_name(self) -> str:
        return "⏸️ Requesting user input"

    def prepare_args(self, args: dict) -> dict:
        return args

    async def process_result(self, raw_result: Any, original_args: dict) -> ToolResult:
        prompt = original_args.get("prompt", "Please provide additional information.")

        events = [
            StreamEvent(
                event_type="input_required",
                execution_id=self.execution_id,
                content=prompt,
                data={
                    "prompt": prompt,
                    "iteration": self.iteration,
                },
            )
        ]

        return ToolResult(
            success=True,
            data={"prompt": prompt, "state": "input_required"},
            is_terminal=True,
            final_answer=None,
            events=events,
            message_content=f"Waiting for user input: {prompt}",
        )
