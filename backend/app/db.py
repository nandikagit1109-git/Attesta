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
    """Create all tables, then add any columns that are new since an older
    schema was created (SQLite ALTER TABLE ADD COLUMN). Keeps an existing demo
    database working across releases without a migration tool."""
    from . import models  # noqa: F401  (register models on the Base metadata)

    Base.metadata.create_all(bind=engine)
    if not _settings.database_url.startswith("sqlite"):
        return
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in inspector.get_table_names():
            mapper = Base.metadata.tables.get(table)
            if mapper is None:
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            for column in mapper.columns:
                if column.name in existing:
                    continue
                col_type = column.type.compile(engine.dialect)
                default = ""
                if column.server_default is not None:
                    default = f" DEFAULT {column.server_default.arg}"
                conn.execute(
                    text(f'ALTER TABLE "{table}" ADD COLUMN "{column.name}" {col_type}{default}')
                )
