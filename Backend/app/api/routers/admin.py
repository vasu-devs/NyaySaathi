from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List, Dict
from app.services.doc_ingestion import save_upload, ingest_file
from app.services.metadata_store import add_document, list_documents as meta_list, delete_document as meta_delete, set_document_approved
from app.api.deps import require_admin
from app.services.vector_store import QdrantStore
from app.services.embedding import get_embedder

router = APIRouter(prefix="/admin", tags=["admin"]) 


@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    _: Dict = Depends(require_admin),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    content = await file.read()
    saved = save_upload(content, file.filename)
    try:
        info = ingest_file(saved, title=title)
        info["approved"] = False
        add_document(info)
        return {"ok": True, "document": info}
    except Exception as e:
        # Best-effort recovery for vector dimension mismatch by recreating the corpus collection
        msg = str(e)
        try:
            if any(x in msg.lower() for x in ["dimension", "vector", "mismatch", "expected"]):
                dim = get_embedder().get_sentence_embedding_dimension()
                store = QdrantStore()  # default corpus collection
                # Import models lazily to avoid import resolution issues during linting
                from qdrant_client.http import models as qmodels
                store.client.recreate_collection(
                    collection_name=store.collection,
                    vectors_config=qmodels.VectorParams(size=dim, distance=qmodels.Distance.COSINE),
                )
                info = ingest_file(saved, title=title)  # retry
                info["approved"] = False
                add_document(info)
                return {"ok": True, "document": info, "recovered": True}
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {msg}")


# Minimal stubs for list/get/delete (metadata persistence will be added later)
@router.get("/documents")
async def list_documents(_: Dict = Depends(require_admin)):
    return {"items": meta_list()}


@router.patch("/documents/{doc_id}/approve")
async def approve_document(doc_id: str, _: Dict = Depends(require_admin)):
    ok = set_document_approved(doc_id, True)
    if not ok:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"ok": True, "doc_id": doc_id, "approved": True}


@router.patch("/documents/{doc_id}/unapprove")
async def unapprove_document(doc_id: str, _: Dict = Depends(require_admin)):
    ok = set_document_approved(doc_id, False)
    if not ok:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"ok": True, "doc_id": doc_id, "approved": False}


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, _: Dict = Depends(require_admin)):
    # Delete embeddings from Qdrant and remove metadata
    store = QdrantStore()
    try:
        store.delete_by_doc_id(doc_id)
    except Exception as e:
        # Continue even if vector deletion fails; surface the error in response
        vec_err = str(e)
    else:
        vec_err = None
    deleted = meta_delete(doc_id)
    return {"ok": deleted, "deleted": doc_id, "vectors_error": vec_err}
