"""
Brain Engine Memory — Three-layer memory system.

Layers:
  - Short-term: session messages (from checkpoint or task history)
  - Long-term: cross-session facts with vector embeddings (pgvector)
  - Episodic: auto-generated summaries of past interactions
"""

from .manager import MemoryManager, MemoryContext
from .llm_helper import make_llm_call

__all__ = ["MemoryManager", "MemoryContext", "make_llm_call"]
