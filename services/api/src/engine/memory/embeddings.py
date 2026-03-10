"""
Embedding generation for long-term memory.

Uses sentence-transformers to generate 768-dim embeddings
for semantic search via pgvector.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_model = None
_model_loading = False

MODEL_NAME = "all-mpnet-base-v2"
EMBEDDING_DIM = 768


def _get_model():
    """Lazy-load the sentence-transformer model."""
    global _model, _model_loading
    if _model is not None:
        return _model
    if _model_loading:
        return None
    _model_loading = True
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
        logger.info(f"Loaded sentence-transformer model: {MODEL_NAME}")
        return _model
    except Exception as e:
        logger.warning(f"Failed to load sentence-transformer: {e}")
        _model_loading = False
        return None


def generate_embedding(text: str) -> Optional[list[float]]:
    """
    Generate an embedding vector for the given text.
    Returns None if the model is not available.
    """
    model = _get_model()
    if not model:
        return None
    try:
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    except Exception as e:
        logger.warning(f"Embedding generation failed: {e}")
        return None


def generate_embeddings_batch(texts: list[str]) -> list[Optional[list[float]]]:
    """Generate embeddings for a batch of texts."""
    model = _get_model()
    if not model:
        return [None] * len(texts)
    try:
        embeddings = model.encode(texts, normalize_embeddings=True)
        return [e.tolist() for e in embeddings]
    except Exception as e:
        logger.warning(f"Batch embedding generation failed: {e}")
        return [None] * len(texts)
