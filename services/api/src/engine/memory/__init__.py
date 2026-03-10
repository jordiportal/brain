"""
Brain Engine Memory — Three-layer memory system.

Layers:
  - Short-term: session messages (from checkpoint or task history)
  - Long-term: cross-session facts with vector embeddings (pgvector)
  - Episodic: auto-generated summaries of past interactions
"""

from .manager import MemoryManager, MemoryContext

__all__ = ["MemoryManager", "MemoryContext"]
