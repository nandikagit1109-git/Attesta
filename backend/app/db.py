"""Database engine and session management (SQLAlchemy 2.x, SQLite default).

PostgreSQL works via the standard DATABASE_URL env; SQLite is the demo
default. The hosted serverless deployment uses /tmp SQLite, which is
ephemeral by hosting design (see docs/ASSUMPTIONS.md #11).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
connect_args = {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}
engine = create_engine(_settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    """FastAPI dependency yielding a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Called at app startup."""
    from . import models  # noqa: F401  (register models on the Base metadata)

    Base.metadata.create_all(bind=engine)
