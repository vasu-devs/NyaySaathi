from __future__ import annotations
from fastapi import APIRouter, Query
from datetime import date, datetime
from typing import Optional
from app.services.nyayshala_generator import generate_for_day, generate_random_for_day, read_for_day, FIELDS
from app.services.rag_engine import clean_legal_response

router = APIRouter(prefix="/nyayshala", tags=["nyayshala"])


@router.get("/daily")
def daily(field: Optional[str] = Query(None), random: Optional[bool] = Query(False)):
    today = date.today()
    if random:
        items = generate_random_for_day(today)
        data = {"date": today.isoformat(), "items": items}
    else:
        data = read_for_day(today)
        if data is None:
            items = generate_for_day(today)
            data = {"date": today.isoformat(), "items": items}
    if field and field in FIELDS:
        data = {**data, "items": [i for i in data["items"] if i["field"] == field]}
    # Sanitize items before returning (handles existing stored items with markdown)
    try:
        clean_items = []
        for it in data.get("items", []) or []:
            txt = clean_legal_response(it.get("content") or "")
            first_line = next((ln.strip() for ln in (txt or "").splitlines() if ln.strip()), "")
            base_title = first_line.rstrip(":")
            if base_title.lower().startswith("title: "):
                base_title = base_title[7:].strip()
            clean_items.append({**it, "title": ((base_title[:80]) or it.get("title") or "NyayShala"), "content": txt})
        return {**data, "items": clean_items}
    except Exception:
        return data


@router.get("/archive")
def archive(date_str: str = Query(..., description="YYYY-MM-DD")):
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    data = read_for_day(d)
    if data is None:
        return {"date": d.isoformat(), "items": []}
    try:
        clean_items = []
        for it in data.get("items", []) or []:
            txt = clean_legal_response(it.get("content") or "")
            first_line = next((ln.strip() for ln in (txt or "").splitlines() if ln.strip()), "")
            base_title = first_line.rstrip(":")
            if base_title.lower().startswith("title: "):
                base_title = base_title[7:].strip()
            clean_items.append({**it, "title": ((base_title[:80]) or it.get("title") or "NyayShala"), "content": txt})
        return {**data, "items": clean_items}
    except Exception:
        return data


@router.post("/generate")
def generate():
    today = date.today()
    items = generate_for_day(today)
    try:
        clean_items = []
        for it in items or []:
            txt = clean_legal_response(it.get("content") or "")
            first_line = next((ln.strip() for ln in (txt or "").splitlines() if ln.strip()), "")
            base_title = first_line.rstrip(":")
            if base_title.lower().startswith("title: "):
                base_title = base_title[7:].strip()
            clean_items.append({**it, "title": ((base_title[:80]) or it.get("title") or "NyayShala"), "content": txt})
        return {"date": today.isoformat(), "items": clean_items}
    except Exception:
        return {"date": today.isoformat(), "items": items}
