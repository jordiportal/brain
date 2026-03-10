"""
Checkpoint — LangGraph durable execution with PostgreSQL.

Uses AsyncPostgresSaver from langgraph-checkpoint-postgres to persist
graph state across executions, enabling:
  - Resume from failure
  - Human-in-the-loop (interrupt / resume)
  - Retry from last checkpoint
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_checkpointer = None
_checkpointer_cm = None


def _get_db_url() -> str:
    """Build a psycopg-compatible connection string for the checkpointer."""
    host = os.getenv("DATABASE_HOST", "localhost")
    port = os.getenv("DATABASE_PORT", "5432")
    name = os.getenv("DATABASE_NAME", "brain_db")
    user = os.getenv("DATABASE_USER", "brain")
    password = os.getenv("DATABASE_PASSWORD", "brain_secret")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


async def init_checkpointer():
    """
    Initialize the async PostgreSQL checkpointer.

    Creates the required tables (checkpoints, checkpoint_blobs,
    checkpoint_writes) if they don't exist.

    Call this once during app startup (lifespan).
    """
    global _checkpointer, _checkpointer_cm
    if _checkpointer is not None:
        return _checkpointer

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        db_url = _get_db_url()
        _checkpointer_cm = AsyncPostgresSaver.from_conn_string(db_url)
        _checkpointer = await _checkpointer_cm.__aenter__()
        await _checkpointer.setup()
        logger.info("LangGraph checkpointer initialized (PostgreSQL)")
    except ImportError:
        logger.warning(
            "langgraph-checkpoint-postgres not installed — "
            "checkpointing disabled. Install with: "
            "pip install langgraph-checkpoint-postgres"
        )
    except Exception as e:
        logger.error(f"Failed to initialize checkpointer: {e}")
        _checkpointer = None
        _checkpointer_cm = None

    return _checkpointer


def get_checkpointer():
    """Get the global checkpointer instance (may be None if not initialized)."""
    return _checkpointer


async def shutdown_checkpointer():
    """Clean up checkpointer connections on shutdown."""
    global _checkpointer, _checkpointer_cm
    if _checkpointer_cm is not None:
        try:
            await _checkpointer_cm.__aexit__(None, None, None)
        except Exception as e:
            logger.warning(f"Error closing checkpointer: {e}")
    _checkpointer = None
    _checkpointer_cm = None
    logger.info("LangGraph checkpointer shut down")
