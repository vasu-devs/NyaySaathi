from __future__ import annotations
import os
import uuid
import hashlib
from typing import List, Dict, Tuple
import fitz  # PyMuPDF
from docx2python import docx2python
from app.core.config import settings
from app.utils.text_splitter import (
    split_text,
    preprocess_legal_text,
    parse_legal_units,
    chunk_units,
    derive_procedural_tags,
)
from app.services.embedding import get_embedder
from app.services.vector_store import QdrantStore


UPLOAD_DIR = settings.storage_dir

os.makedirs(UPLOAD_DIR, exist_ok=True)


def _checksum(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_pdf(path: str) -> str:
    doc = fitz.open(path)
    texts: List[str] = []
    for page in doc:
        texts.append(page.get_text())
    return "\n".join(texts)


def _read_docx(path: str) -> str:
    with docx2python(path) as doc:
        parts: List[str] = []
        for sec in doc.body:
            for para in sec:
                parts.append(" ".join(para))
        return "\n".join(parts)


def _read_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def extract_text(path: str, mimetype: str | None = None) -> str:
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".pdf":
            return _read_pdf(path)
        if ext in (".docx",):
            return _read_docx(path)
        if ext in (".txt", ".md"):
            return _read_txt(path)
    except Exception as e:
        raise RuntimeError(f"Failed to parse {path}: {e}")
    raise RuntimeError(f"Unsupported file type: {ext}")


def ingest_file(
    saved_path: str,
    title: str | None = None,
    doc_id: str | None = None,
    collection: str | None = None,
    progress_cb: callable | None = None,
    batch_size: int = 64,
) -> Dict:
    """Parse -> split -> embed -> upsert into Qdrant in batches with optional progress callback.

    progress_cb, if provided, will be called with a dict including fields like:
    { 'stage': 'extract' | 'split' | 'index' | 'done', 'total_chunks': int, 'ingested': int, 'percent': int }
    """
    # Extract
    if progress_cb:
        progress_cb({"stage": "extract"})
    text = extract_text(saved_path)

    # Prefer legal-aware splitting with enriched metadata
    chunks_with_meta: List[Tuple[str, Dict]] = []
    try:
        units = parse_legal_units(text)
        # Clean each unit body conservatively to remove noise while keeping headings
        for u in units:
            u["text"] = preprocess_legal_text(u.get("text", ""))
        if units and any(u.get("unit_type") in ("Article", "Section") for u in units):
            chunks_with_meta = chunk_units(units, target_chars=1600, overlap=200)
    except Exception:
        # Fall back to simple splitter below
        chunks_with_meta = []

    if chunks_with_meta:
        chunks = [c for c, _ in chunks_with_meta]
    else:
        # Fallback: preprocess full text then simple split
        clean_full = preprocess_legal_text(text)
        chunks = split_text(clean_full)
        # create placeholder meta
        chunks_with_meta = [(c, {"unit_type": "Prose"}) for c in chunks]

    total_chunks = len(chunks_with_meta)
    if progress_cb:
        progress_cb({"stage": "split", "total_chunks": total_chunks, "ingested": 0, "percent": 0})

    # Prepare embedding and collection
    embedder = get_embedder()
    vector_size = embedder.get_sentence_embedding_dimension()
    store = QdrantStore(collection=collection)
    store.ensure_collection(vector_size)

    if not doc_id:
        doc_id = str(uuid.uuid4())
    checksum = _checksum(saved_path)

    # Embed + upsert in batches, reporting progress
    ingested = 0
    title_value = title or os.path.basename(saved_path)
    for start in range(0, total_chunks, batch_size):
        end = min(start + batch_size, total_chunks)
        batch_chunks_meta = chunks_with_meta[start:end]
        batch_chunks = [c for c, _ in batch_chunks_meta]
        # Embed this batch
        vectors = embedder.encode(
            batch_chunks,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True,
        ).tolist()

        # Build ids/payloads for this batch
        ids: List[str] = []
        payloads: List[Dict] = []
        for i_rel, ((chunk, meta), vec) in enumerate(zip(batch_chunks_meta, vectors)):
            idx = start + i_rel
            # Qdrant point id must be an unsigned integer or a UUID. Use UUID per chunk.
            point_id = str(uuid.uuid4())
            ids.append(point_id)
            extra: Dict = {
                "unit_type": meta.get("unit_type"),
                "heading": meta.get("heading"),
                "part": meta.get("part"),
                "chapter": meta.get("chapter"),
            }
            ident = meta.get("identifier")
            if ident:
                if meta.get("unit_type") == "Article":
                    extra["article"] = ident
                if meta.get("unit_type") == "Section":
                    extra["section"] = ident

            # Derive procedural/reasoning tags for retrieval
            tags = derive_procedural_tags(chunk, meta.get("unit_type"), meta.get("identifier"), title_value)

            payload = {
                "doc_id": doc_id,
                "chunk_id": idx,
                "text": chunk,
                "title": title_value,
                "source_path": saved_path,
                "checksum": checksum,
                "tags": tags,
            }
            payload.update(extra)
            payloads.append(payload)

        # Upsert this batch
        store.upsert_points(ids, vectors, payloads)

        ingested = end
        if progress_cb:
            percent = int(max(0, min(100, round((ingested / max(1, total_chunks)) * 100))))
            progress_cb({
                "stage": "index",
                "total_chunks": total_chunks,
                "ingested": ingested,
                "percent": percent,
            })

    if progress_cb:
        progress_cb({"stage": "done", "total_chunks": total_chunks, "ingested": total_chunks, "percent": 100})

    return {
        "doc_id": doc_id,
        "title": title_value,
        "chunks": total_chunks,
        "checksum": checksum,
        "path": saved_path,
    }


def save_upload(file_bytes: bytes, filename: str) -> str:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    # disambiguate
    base, ext = os.path.splitext(filename)
    safe_base = base.replace(" ", "_")
    target = os.path.join(UPLOAD_DIR, f"{safe_base}{ext}")
    i = 1
    while os.path.exists(target):
        target = os.path.join(UPLOAD_DIR, f"{safe_base}_{i}{ext}")
        i += 1
    with open(target, "wb") as f:
        f.write(file_bytes)
    return target
