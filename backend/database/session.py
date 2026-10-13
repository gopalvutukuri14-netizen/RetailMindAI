import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Ensure root .env is loaded reliably
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

Base = declarative_base()


def get_database_url() -> str:
    """
    Retrieve and normalize the authoritative database URL.
    Strict rule: Cloud PostgreSQL is authoritative. No silent fallback to local SQLite.
    """
    url = os.getenv("DATABASE_URL", "").strip()

    if not url:
        # Check if running in an isolated test environment
        is_testing = (
            os.getenv("TESTING", "").lower() in ("true", "1")
            or "PYTEST_CURRENT_TEST" in os.environ
        )
        if is_testing:
            return "sqlite:///:memory:"

        raise RuntimeError(
            "Authoritative DATABASE_URL is not configured in the root .env. "
            "Cloud PostgreSQL is required for SmartPick application data. "
            "Silent fallback to local SQLite is disabled."
        )

    # Normalize Heroku/Supabase/Neon style postgres:// URLs for SQLAlchemy 2.x and psycopg
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+psycopg://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    return url


DATABASE_URL = get_database_url()

# Configure engine with pooling and health checks
engine_kwargs = {
    "pool_pre_ping": True,
}

if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 300,
        "pool_timeout": 30,
    })

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency to yield database sessions with safe teardown."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
