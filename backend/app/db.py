"""SQLite engine and session helpers."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.models import Base


def sqlite_file_path(database_url: str) -> Path | None:
    if not database_url.startswith("sqlite"):
        return None
    if ":memory:" in database_url:
        return None
    raw = database_url.removeprefix("sqlite:///")
    if not raw:
        return None
    return Path(raw)


def make_engine(settings: Settings) -> Engine:
    url = settings.database_url
    connect_args: dict = {}
    engine_kwargs: dict = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if ":memory:" in url:
            engine_kwargs["poolclass"] = StaticPool
        else:
            file_path = sqlite_file_path(url)
            if file_path is not None:
                file_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(url, connect_args=connect_args, **engine_kwargs)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def session_scope(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def ensure_schema(engine: Engine) -> None:
    """Create tables and add columns introduced after the first release."""
    Base.metadata.create_all(engine)
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as connection:
        rows = connection.execute(text("PRAGMA table_info(segments)")).fetchall()
        columns = {row[1] for row in rows}
        if rows and "translation_zh" not in columns:
            connection.execute(text("ALTER TABLE segments ADD COLUMN translation_zh TEXT"))
