"""Database engine, session factory, and the FastAPI session dependency."""

import sqlite3
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# SQLite refuses to reuse a connection across threads unless we opt out of the
# check; FastAPI runs sync endpoints in a threadpool, so this is required.
_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=_connect_args, future=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    # Keep attributes loaded after commit so routes can serialise an object
    # without triggering another SELECT.
    expire_on_commit=False,
)


@event.listens_for(Engine, "connect")
def _configure_sqlite(dbapi_connection, connection_record) -> None:
    """SQLite ships with foreign key enforcement OFF.

    Without this pragma every ``ON DELETE CASCADE`` in our schema is silently
    ignored and deleting a meeting would orphan its sentences. It has to be set
    per connection, hence the event listener rather than a one-off statement.
    """
    if not isinstance(dbapi_connection, sqlite3.Connection):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def get_db() -> Generator[Session, None, None]:
    """Yield a session per request and always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
