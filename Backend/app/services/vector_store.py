from __future__ import annotations
from typing import List, Dict, Optional, Callable, TypeVar
import time
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from app.core.config import settings


class QdrantStore:
    def __init__(self, collection: Optional[str] = None):
        # Slightly longer timeout to avoid transient refused connections during container startup
        self.client = QdrantClient(url=settings.qdrant_url, timeout=20.0)
        self.collection = collection or settings.qdrant_corpus_collection

    def _with_retries(self, fn: Callable, *args, **kwargs):
        """Execute a client call with brief retries to smooth over container cold starts.

        Retries: up to 3 attempts with 0.5s backoff (total ~1s). Keeps exceptions opaque otherwise.
        """
        attempts = 3
        delay = 0.5
        last_exc = None
        for i in range(attempts):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_exc = e
                if i < attempts - 1:
                    time.sleep(delay)
                else:
                    raise

    def ensure_collection(self, vector_size: int, distance: qmodels.Distance = qmodels.Distance.COSINE):
        exists = False
        try:
            info = self._with_retries(self.client.get_collection, self.collection)
            exists = True
            # If exists but vector size differs, we should recreate (skip here for simplicity)
        except Exception:
            exists = False
        if not exists:
            self._with_retries(
                self.client.recreate_collection,
                collection_name=self.collection,
                vectors_config=qmodels.VectorParams(size=vector_size, distance=distance),
            )

    def upsert_points(self, ids: List[str], vectors: List[List[float]], payloads: List[Dict]):
        self._with_retries(
            self.client.upsert,
            collection_name=self.collection,
            points=qmodels.Batch(
                ids=ids,
                vectors=vectors,
                payloads=payloads,
            ),
        )

    def search(self, vector: List[float], top_k: int = 6, filter_: Optional[qmodels.Filter] = None) -> List[Dict]:
        res = self._with_retries(
            self.client.search,
            collection_name=self.collection,
            query_vector=vector,
            limit=top_k,
            query_filter=filter_,
            with_payload=True,
        )
        out: List[Dict] = []
        for p in res:
            payload = p.payload or {}
            out.append(
                {
                    "doc_id": payload.get("doc_id"),
                    "chunk_id": payload.get("chunk_id"),
                    "text": payload.get("text"),
                    "score": p.score,
                    "meta": payload,
                }
            )
        return out

    def delete_by_doc_id(self, doc_id: str) -> int:
        """Delete all points in this collection that match the given doc_id. Returns number of points scheduled for deletion (best-effort)."""
        cond = qmodels.Filter(must=[qmodels.FieldCondition(key="doc_id", match=qmodels.MatchValue(value=doc_id))])
        res = self._with_retries(
            self.client.delete,
            collection_name=self.collection,
            points_selector=qmodels.FilterSelector(filter=cond),
            wait=True,
        )
        # Qdrant returns operation result; count may not be provided, so return 0/1 semantics
        return getattr(res, "status", None) is not None and 1 or 0
