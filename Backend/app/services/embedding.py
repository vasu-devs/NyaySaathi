from __future__ import annotations
from sentence_transformers import SentenceTransformer
import torch
from functools import lru_cache
from app.core.config import settings


@lru_cache(maxsize=1)
def get_embedder() -> SentenceTransformer:
    """Return a SentenceTransformer embedder with robust fallbacks.

    Workaround PyTorch meta-tensor move errors by preferring CPU init and
    falling back to a smaller, stable model if needed.
    """
    # Prefer CPU on Windows/dev to avoid CUDA/mps/device-map quirks
    preferred_device = getattr(settings, "embed_device", "cpu") or "cpu"

    primary_model = getattr(settings, "embed_model", "BAAI/bge-m3")
    fallbacks = [
        "sentence-transformers/all-MiniLM-L6-v2",  # very stable and light
    ]

    def _try_load(name: str) -> SentenceTransformer:
        # Force CPU to avoid meta-tensor to() issues in recent torch/transformers
        return SentenceTransformer(name, device="cpu", trust_remote_code=True)

    # Try primary
    try:
        return _try_load(primary_model)
    except NotImplementedError:
        # Meta-tensor or similar device move issue; try fallbacks
        pass
    except Exception:
        # Other init issues; try fallbacks
        pass

    # Try fallback models
    for fb in fallbacks:
        try:
            return _try_load(fb)
        except Exception:
            continue

    # As a last resort, raise a clear error to surface in logs
    raise RuntimeError(
        "Failed to initialize embedding model. Try installing compatible torch/transformers versions or set EMBED_MODEL to a smaller model like 'sentence-transformers/all-MiniLM-L6-v2'."
    )


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = get_embedder()
    embs = model.encode(texts, batch_size=64, convert_to_numpy=True, show_progress_bar=False, normalize_embeddings=True)
    return embs.tolist()


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
