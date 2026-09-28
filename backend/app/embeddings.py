"""Server-side ONNX embeddings. The model must be cached during setup/build."""
import math
import os
from functools import lru_cache
from threading import RLock

from app.config import get_settings


class EmbeddingError(RuntimeError):
    pass


_model_lock = RLock()


@lru_cache(maxsize=1)
def _cached_model():
    from fastembed import TextEmbedding
    return TextEmbedding(model_name=get_settings().embedding_model,
                         cache_dir=os.getenv("EMBEDDING_CACHE_DIR"),
                         threads=2, local_files_only=True)


def local_model():
    # lru_cache alone permits duplicate initialization on concurrent cold calls.
    with _model_lock:
        return _cached_model()


def embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    try:
        with _model_lock:
            vectors = [item.tolist() for item in local_model().embed(texts, batch_size=8)]
        if len(vectors) != len(texts) or any(
            len(v) != get_settings().embedding_dimensions or not any(v)
            or not all(math.isfinite(x) for x in v) for v in vectors
        ):
            raise ValueError("Invalid local embedding")
        return vectors
    except Exception as exc:
        raise EmbeddingError("Local semantic search is temporarily unavailable.") from exc
