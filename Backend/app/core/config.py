from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List

class Settings(BaseSettings):
    # API
    api_prefix: str = "/api"
    cors_origins: List[str] = ["http://localhost:5173"]

    # LLM provider
    llm_provider: str = Field("google", description="openai|google")
    # Prefer v1 model id form for Gemini 2.0 Flash
    llm_model: str = Field("models/gemini-2.0-flash")
    llm_max_output_tokens: int = Field(6144, description="Maximum tokens to generate in responses")
    enable_markdown_rendering: bool = Field(False, description="Toggle Markdown rendering vs plain text sanitization")
    openai_api_key: str | None = None
    google_api_key: str | None = None

    # Stores
    qdrant_url: str = "http://localhost:6333"
    redis_url: str = "redis://localhost:6379/0"
    storage_dir: str = ".data/uploads"
    qdrant_corpus_collection: str = "corpus"

    # Auth
    jwt_secret: str = "change-me-dev-secret"
    jwt_expire_minutes: int = 120
    admin_email: str = "admin@example.com"
    admin_password: str = "admin123"

    class Config:
        env_file = ".env"

settings = Settings()
