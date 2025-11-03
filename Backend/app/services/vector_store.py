from __future__ import annotations
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from app.core.config import settings


class QdrantStore:
    def __init__(self, collection: Optional[str] = None):
        self.client = QdrantClient(url=settings.qdrant_url)
        self.collection = collection or settings.qdrant_corpus_collection

    def ensure_collection(self, vector_size: int, distance: qmodels.Distance = qmodels.Distance.COSINE):
        exists = False
        try:
            info = self.client.get_collection(self.collection)
            exists = True
            # If exists but vector size differs, we should recreate (skip here for simplicity)
        except Exception:
            exists = False
        if not exists:
            self.client.recreate_collection(
                collection_name=self.collection,
                vectors_config=qmodels.VectorParams(size=vector_size, distance=distance),
            )

    def upsert_points(self, ids: List[str], vectors: List[List[float]], payloads: List[Dict]):
        self.client.upsert(
            collection_name=self.collection,
            points=qmodels.Batch(
                ids=ids,
                vectors=vectors,
                payloads=payloads,
            ),
        )

    def search(self, vector: List[float], top_k: int = 6, filter_: Optional[qmodels.Filter] = None) -> List[Dict]:
        res = self.client.search(
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
        res = self.client.delete(
            collection_name=self.collection,
            points_selector=qmodels.FilterSelector(filter=cond),
            wait=True,
        )
        # Qdrant returns operation result; count may not be provided, so return 0/1 semantics
        return getattr(res, "status", None) is not None and 1 or 0
