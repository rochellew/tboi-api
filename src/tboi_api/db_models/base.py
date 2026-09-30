"""Declarative base shared by every model."""

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models; holds the shared table metadata."""


def create_sqlite_engine(path: str, echo: bool = False) -> Engine:
    """Create a SQLite engine with foreign key enforcement turned on."""
    engine = create_engine(f"sqlite:///{path}", echo=echo)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys = ON")

    return engine
