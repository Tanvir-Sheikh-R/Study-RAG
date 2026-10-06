"""E5 embeddings loaded from the project's model_cache.

The notebook's E5Embeddings adds the "query: " / "passage: " prefixes so the stored
chunk text stays clean. Same behaviour here, with a lock because a single model
instance is shared across request threads.
"""

from __future__ import annotations

import threading
from functools import lru_cache

import torch

from backend.config import E5_PASSAGE_PREFIX, E5_QUERY_PREFIX, EMBEDDING_MODEL, MODEL_CACHE

_model_lock = threading.Lock()
_model = None


def get_model():
    """Load multilingual-e5-large once, from model_cache, on the best device."""
    global _model
    with _model_lock:
        if _model is None:
            from sentence_transformers import SentenceTransformer

            device = "cuda" if torch.cuda.is_available() else "cpu"
            _model = SentenceTransformer(
                EMBEDDING_MODEL, cache_folder=str(MODEL_CACHE), device=device
            )
        return _model


@lru_cache(maxsize=1)
def model_info() -> dict[str, object]:
    model = get_model()
    dimension_method = getattr(model, "get_embedding_dimension", None)
    if dimension_method is None:
        dimension_method = model.get_sentence_embedding_dimension
    return {
        "model": EMBEDDING_MODEL,
        "device": str(getattr(model, "device", "cpu")),
        "dimension": int(dimension_method()),
    }


def warm_up() -> dict[str, object]:
    return model_info()


def encode_passages(texts: list[str]):
    model = get_model()
    with _model_lock:
        return model.encode(
            [E5_PASSAGE_PREFIX + text for text in texts],
            normalize_embeddings=True,
            show_progress_bar=False,
        )


def encode_query(text: str):
    model = get_model()
    with _model_lock:
        return model.encode(E5_QUERY_PREFIX + text, normalize_embeddings=True)
