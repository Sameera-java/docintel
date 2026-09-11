"""
Database engine/session setup using SQLAlchemy.
Defaults to SQLite (zero-config, file-based) but DATABASE_URL can be swapped
for Postgres/MySQL in production without touching any other code.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Called once on app startup."""
    from app.models import document  # noqa: F401 (ensures model is registered)
    Base.metadata.create_all(bind=engine)
