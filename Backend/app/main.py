from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routers.chatbot import router as chat_router
from app.api.routers.admin import router as admin_router
from app.api.routers.health import router as health_router
from app.api.routers.nyaylens import router as lens_router
from app.api.routers.auth import router as auth_router
from app.api.routers.nyayshala import router as shala_router
from app.api.routers.client_config import router as client_cfg_router
from datetime import date
import threading
from app.services.nyayshala_generator import read_for_day, generate_for_day

app = FastAPI(title="Nyay RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)
app.include_router(lens_router, prefix=settings.api_prefix)
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(shala_router, prefix=settings.api_prefix)
app.include_router(health_router)
app.include_router(client_cfg_router, prefix=settings.api_prefix)


@app.get("/health/live")
def live():
    return {"ok": True}


@app.on_event("startup")
def warmup_daily_nyayshala():
    """Warm the daily NyayShala cache in the background to keep first loads instant."""
    def _worker():
        try:
            today = date.today()
            if not read_for_day(today):
                # Generate and persist today's set (sequential; only once a day)
                generate_for_day(today, persist=True, randomize=False)
        except Exception:
            # Silence warmup errors; normal requests can still generate on-demand
            pass
    threading.Thread(target=_worker, name="nyayshala-warmup", daemon=True).start()
