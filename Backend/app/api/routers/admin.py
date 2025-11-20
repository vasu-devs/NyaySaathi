from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from typing import List, Dict
from app.services.doc_ingestion import save_upload, ingest_file
from app.services.metadata_store import add_document, list_documents as meta_list, delete_document as meta_delete, set_document_approved
from app.api.deps import require_admin
from app.services.vector_store import QdrantStore
from app.services.embedding import get_embedder

router = APIRouter(prefix="/admin", tags=["admin"]) 


@router.post("/documents")
async def upload_document(
    tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    _: Dict = Depends(require_admin),
):
    print(f"Received upload request: {file.filename}")
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    content = await file.read()
    print(f"Read {len(content)} bytes")
    saved = save_upload(content, file.filename)

    import uuid
    doc_id = str(uuid.uuid4())
    
    # Add initial "processing" metadata so it shows up immediately
    initial_info = {
        "doc_id": doc_id,
        "title": title or file.filename,
        "path": saved,
        "approved": False,
        "status": "processing",
        "chunks": 0
    }
    add_document(initial_info)

    def _bg():
        print(f"[BG TASK] Starting ingestion for doc_id={doc_id}, file={saved}")
        try:
            # Pass doc_id to reuse it
            print(f"[BG TASK] Calling ingest_file...")
            info = ingest_file(saved, title=title, doc_id=doc_id)
            print(f"[BG TASK] Ingestion complete. Chunks: {info.get('chunks', 0)}")
            info["approved"] = False
            info["status"] = "ready"
            print(f"[BG TASK] Updating metadata...")
            add_document(info)
            print(f"[BG TASK] Metadata updated successfully")
        except Exception as e:
            print(f"[BG TASK] Ingestion failed: {e}")
            import traceback
            traceback.print_exc()
            initial_info["status"] = "error"
            initial_info["error"] = str(e)
            add_document(initial_info)

    tasks.add_task(_bg)
    
    return {"ok": True, "message": "Ingestion started in background", "doc_id": doc_id}



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
