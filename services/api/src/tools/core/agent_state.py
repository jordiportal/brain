"""
Agent State Tools — Read/write persistent typed state per agent+context.

These tools allow agents to store and retrieve structured data
that persists across sessions for the same agent+context pair.
"""

import json
import structlog

logger = structlog.get_logger()


async def get_agent_state(agent_id: str = "", context_id: str = "", key: str = "", **kwargs) -> dict:
    """Get the persistent state (or a specific key) for an agent+context."""
    _agent_id = agent_id or kwargs.get("_agent_id", "")
    _context_id = context_id or kwargs.get("_context_id", "")

    if not _agent_id or not _context_id:
        return {"success": False, "error": "agent_id and context_id are required"}

    try:
        from ...db.repositories.agent_states import AgentStateRepository
        state_obj = await AgentStateRepository.get(_agent_id, _context_id)

        if not state_obj:
            return {"success": True, "state": {}, "key": key, "value": None}

        if key:
            return {
                "success": True,
                "key": key,
                "value": state_obj.state.get(key),
                "state_keys": list(state_obj.state.keys()),
            }

        return {"success": True, "state": state_obj.state}
    except Exception as e:
        logger.error(f"get_agent_state error: {e}")
        return {"success": False, "error": str(e)}


async def update_agent_state(
    agent_id: str = "",
    context_id: str = "",
    key: str = "",
    value: str = "",
    data: dict = None,
    **kwargs,
) -> dict:
    """Update the persistent state for an agent+context. Set a single key or merge a dict."""
    _agent_id = agent_id or kwargs.get("_agent_id", "")
    _context_id = context_id or kwargs.get("_context_id", "")

    if not _agent_id or not _context_id:
        return {"success": False, "error": "agent_id and context_id are required"}

    try:
        from ...db.repositories.agent_states import AgentStateRepository

        updates = {}
        if data and isinstance(data, dict):
            updates = data
        elif key:
            parsed_value = value
            try:
                parsed_value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                pass
            updates = {key: parsed_value}
        else:
            return {"success": False, "error": "Provide key+value or data dict"}

        result = await AgentStateRepository.update_partial(_agent_id, _context_id, updates)
        return {
            "success": True,
            "updated_keys": list(updates.keys()),
            "state": result.state if result else updates,
        }
    except Exception as e:
        logger.error(f"update_agent_state error: {e}")
        return {"success": False, "error": str(e)}


AGENT_STATE_TOOLS = {
    "get_agent_state": {
        "id": "get_agent_state",
        "name": "get_agent_state",
        "description": "Get persistent state for the current agent and context. Use to recall information stored across sessions.",
        "parameters": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID (usually auto-filled)"},
                "context_id": {"type": "string", "description": "Context/session ID (usually auto-filled)"},
                "key": {"type": "string", "description": "Optional: get a specific key from the state"},
            },
            "required": [],
        },
        "handler": get_agent_state,
    },
    "update_agent_state": {
        "id": "update_agent_state",
        "name": "update_agent_state",
        "description": "Store persistent data for the current agent and context. Data survives across sessions. Use to remember user preferences, project state, accumulated results, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID (usually auto-filled)"},
                "context_id": {"type": "string", "description": "Context/session ID (usually auto-filled)"},
                "key": {"type": "string", "description": "State key to set"},
                "value": {"type": "string", "description": "Value to store (JSON string for complex data)"},
                "data": {"type": "object", "description": "Alternative: merge a dict into state"},
            },
            "required": [],
        },
        "handler": update_agent_state,
    },
}
