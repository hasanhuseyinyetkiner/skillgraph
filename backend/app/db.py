"""Engine, migrations, and graph-version updates."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.models import GraphMeta, utcnow


def ensure_sqlite_parent(database_url: str) -> None:
    if not database_url.startswith("sqlite:///"):
        return
    raw = database_url.removeprefix("sqlite:///")
    if raw in {":memory:", ""} or raw.startswith("file:"):
        return
    Path(raw).parent.mkdir(parents=True, exist_ok=True)


def make_engine(database_url: str) -> Engine:
    ensure_sqlite_parent(database_url)
    kwargs: dict[str, object] = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        # timeout (seconds) fails locked opens instead of hanging forever when
        # a second local process competes for the same SQLite file.
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 5.0}
        kwargs["poolclass"] = NullPool
    engine = create_engine(database_url, **kwargs)
    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def run_migrations(database_url: str) -> None:
    import os

    from alembic import command
    from alembic.config import Config

    ensure_sqlite_parent(database_url)
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    # env.py prefers DATABASE_URL. Pin it for this call so tests can target a
    # temporary database even when the shell already has DATABASE_URL set.
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        command.upgrade(config, "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous


def bump_graph_version(session: Session) -> int:
    """Increment the ontology version in the caller's transaction."""

    meta = session.get(GraphMeta, 1)
    if meta is None:
        meta = GraphMeta(id=1, graph_version=1, updated_at=utcnow())
        session.add(meta)
    else:
        meta.graph_version += 1
        meta.updated_at = utcnow()
    session.flush()
    return int(meta.graph_version)


def current_graph_version(session: Session) -> int:
    value = session.scalar(select(GraphMeta.graph_version).where(GraphMeta.id == 1))
    return int(value or 0)
