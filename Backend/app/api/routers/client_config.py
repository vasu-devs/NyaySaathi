from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["config"])


@router.get("/client-config")
def client_config():
    """Public client configuration (safe flags only). Always returns a stable payload."""
    markdown = False
    try:
        markdown = bool(getattr(settings, "enable_markdown_rendering", False))
    except Exception:
        # Never fail this endpoint; default to false if settings not available
        markdown = False
    return {
        "markdown": markdown,
    }
