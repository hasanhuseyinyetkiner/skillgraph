"""SQLite by default. PostgreSQL when SKILLGRAPH_TEST_DATABASE_URL is set."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from app.db import make_engine, run_migrations
from app.main import create_app
from app.models import Base
from app.settings import Settings
from fastapi.testclient import TestClient
from sqlalchemy import text


def database_url_for(tmp_path: Path) -> str:
    configured = os.environ.get("SKILLGRAPH_TEST_DATABASE_URL", "")
    if configured.startswith("postgresql"):
        return configured
    return "sqlite:///" + (tmp_path / "skillgraph.db").as_posix()


def reset_database(url: str) -> None:
    run_migrations(url)
    engine = make_engine(url)
    with engine.begin() as connection:
        if engine.dialect.name == "postgresql":
            names = ", ".join(Base.metadata.tables)
            connection.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
        else:
            connection.execute(text("PRAGMA foreign_keys=OFF"))
            for table in reversed(Base.metadata.sorted_tables):
                connection.execute(table.delete())
            connection.execute(text("PRAGMA foreign_keys=ON"))
        connection.execute(
            text(
                "INSERT INTO graph_meta (id, graph_version, updated_at) VALUES (1, 0, CURRENT_TIMESTAMP)"
            )
        )
    engine.dispose()


def build_settings(url: str, *, auto_seed: bool = True) -> Settings:
    return Settings(
        app_env="test",
        database_url=url,
        host="127.0.0.1",
        port=8105,
        allow_network_bind=False,
        auto_seed=auto_seed,
        run_migrations=True,
        embeddings_enabled=False,
    )


@pytest.fixture
def client(tmp_path: Path):
    url = database_url_for(tmp_path)
    reset_database(url)
    application = create_app(build_settings(url))
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture
def two_clients(tmp_path: Path):
    configured = os.environ.get("SKILLGRAPH_TEST_DATABASE_URL", "")
    url = configured if configured.startswith("postgresql") else "sqlite:///" + (tmp_path / "shared.db").as_posix()
    reset_database(url)
    app_a = create_app(build_settings(url))
    app_b = create_app(build_settings(url))
    with TestClient(app_a) as client_a, TestClient(app_b) as client_b:
        yield client_a, client_b
