"""
SQLAlchemy engine, session factory, and dependency injection helpers.

The engine is configured for both PostgreSQL (production / Neon) and
SQLite (local development fallback). Connection pooling parameters are
read from environment variables via app.config.Settings.
"""

from __future__ import annotations

import logging
from typing import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ..config import settings

logger = logging.getLogger(__name__)


def _build_engine() -> Engine:
    """Build a SQLAlchemy engine appropriate for the configured DATABASE_URL."""
    db_url = settings.DATABASE_URL
    connect_args: dict = {}

    if db_url.startswith("sqlite"):
        # SQLite needs check_same_thread=False for FastAPI's threaded dev server.
        connect_args["check_same_thread"] = False
        engine_obj = create_engine(
            db_url,
            connect_args=connect_args,
            future=True,
        )
    else:
        engine_obj = create_engine(
            db_url,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_recycle=settings.DB_POOL_RECYCLE,
            pool_pre_ping=settings.DB_POOL_PRE_PING,
            future=True,
        )
    logger.info("Database engine initialised for %s", db_url.split("@")[-1])
    return engine_obj


engine: Engine = _build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a SQLAlchemy session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Create all tables defined on Base.metadata.

    Safe to run on every startup; existing tables are not modified. For
    schema migrations in production, use Alembic.
    """
    # Import models so they are registered with Base.metadata before create_all.
    from ..models import activity_log, admin, print_log, printer, user_profile  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _apply_lightweight_migrations()
    logger.info("Database tables ensured (create_all complete).")


def _apply_lightweight_migrations() -> None:
    """
    Apply additive, idempotent column migrations for local/prototype setups.

    This keeps existing SQLite/Postgres databases usable without forcing
    Alembic for every small schema extension.
    """
    insp = inspect(engine)
    if "print_logs" not in insp.get_table_names():
        return

    existing_cols = {col["name"] for col in insp.get_columns("print_logs")}
    ddl: list[str] = []
    if "display_username" not in existing_cols:
        ddl.append("ALTER TABLE print_logs ADD COLUMN display_username VARCHAR(128)")
    if "user_limit_exceeded" not in existing_cols:
        if engine.dialect.name.startswith("sqlite"):
            ddl.append("ALTER TABLE print_logs ADD COLUMN user_limit_exceeded BOOLEAN NOT NULL DEFAULT 0")
        else:
            ddl.append("ALTER TABLE print_logs ADD COLUMN user_limit_exceeded BOOLEAN NOT NULL DEFAULT FALSE")

    if not ddl:
        return

    with engine.begin() as conn:
        for statement in ddl:
            conn.execute(text(statement))
    logger.info("Applied additive DB migrations: %s", ", ".join(ddl))
