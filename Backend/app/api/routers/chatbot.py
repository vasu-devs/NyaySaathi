from fastapi import APIRouter, Body, Query
from sse_starlette.sse import EventSourceResponse
import json
from app.services.rag_engine import answer, retrieve_context
from app.core.config import settings
from app.services.llm_client import LLMClient

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/stream")
def stream_chat(query: str = Query(..., min_length=1)):
    """Temporarily disable streaming and previews. Frontend will fall back to one-shot /chat/ask."""

    def event_gen():
        # Immediately end the stream; no tokens or previews are emitted
        yield {"event": "end", "data": "[DONE]"}

    return EventSourceResponse(event_gen())


@router.post("/ask")
def ask_chat(query: str = Body(..., embed=True)):
    try:
        text = answer(query, stream=False)
    except Exception as e:
        # Ensure the endpoint never crashes the client; return a safe message
        text = (
            "Sorry, I can't complete this right now. Please refer to official Government of India legal resources:\n"
            "- India Code: https://www.indiacode.nic.in/ (official repository of Central Acts)\n"
            "- Legislative Department: https://legislative.gov.in (includes the Constitution of India)"
        )
    return {"answer": text}


@router.get("/debug/retrieve")
def debug_retrieve(query: str = Query(..., min_length=1), top_k: int = Query(6, ge=1, le=20)):
    """Return top retrieved contexts (without calling the LLM). Useful for debugging RAG."""
    ctx = retrieve_context(query, top_k=top_k)
    return {"contexts": ctx}


@router.get("/ask")
def ask_chat_get(
    query: str | None = Query(None, min_length=1),
    q: str | None = Query(None, min_length=1, description="Compatibility alias for 'query'")
):
    # Accept both 'query' and legacy 'q' as input; prefer 'query' when both provided
    final_query = query or q
    if not final_query:
        # Mirror prior behavior: avoid raising; provide safe guidance instead
        return {
            "answer": (
                "Please provide a non-empty 'query' parameter. For legal references, see:\n"
                "- India Code: https://www.indiacode.nic.in/\n"
                "- Legislative Department: https://legislative.gov.in"
            )
        }
    try:
        text = answer(final_query, stream=False)
    except Exception:
        text = (
            "Sorry, I can't complete this right now. Please refer to official Government of India legal resources:\n"
            "- India Code: https://www.indiacode.nic.in/ (official repository of Central Acts)\n"
            "- Legislative Department: https://legislative.gov.in (includes the Constitution of India)"
        )
    return {"answer": text}


@router.get("/debug/llm")
def debug_llm():
    """Return which provider/model are configured and whether keys are present (no secrets)."""
    info = {
        "env_provider": settings.llm_provider,
        "env_model": settings.llm_model,
        "has_openai_key": bool(settings.openai_api_key),
        "has_google_key": bool(settings.google_api_key),
    }
    try:
        client = LLMClient()
        info["resolved_provider"] = getattr(client, "provider", None)
        info["resolved_model"] = getattr(client, "model", None)
    except Exception as e:
        info["init_error"] = str(e)[:200]
    return info
