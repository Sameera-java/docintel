"""
Central application configuration.
All secrets/config values are read from environment variables (never hardcoded),
per the assignment's "no secrets committed to source" requirement.
"""
import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()  # picks up a local .env file if present (no-op if it doesn't exist)


class Settings:
    # LLM provider (Gemini free tier) — used for structured field/table extraction
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # Database (SQLite by default — swappable via env var for Postgres/MySQL later)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./docintel.db")

    # File handling limits (from spec: PDF/JPG/PNG, up to 3 pages)
    MAX_PAGES: int = int(os.getenv("MAX_PAGES", "3"))
    ALLOWED_CONTENT_TYPES: tuple = (
        "application/pdf",
        "image/jpeg",
        "image/jpg",
        "image/png",
    )
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "15"))

    # Financial validation tolerance — small variances are allowed due to rounding
    VALIDATION_TOLERANCE: float = float(os.getenv("VALIDATION_TOLERANCE", "1.0"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    

    APP_NAME: str = "Document Intelligence Platform"
    API_PREFIX: str = "/api/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
