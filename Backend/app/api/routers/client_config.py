from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["config"])


@router.get("/client-config")
def client_config():
    """Public client configuration (safe flags only)."""
    return {
        "markdown": bool(settings.enable_markdown_rendering),
    }
