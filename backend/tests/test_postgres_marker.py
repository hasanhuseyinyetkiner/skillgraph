import os

import pytest
from app.db import make_engine
from sqlalchemy import text


@pytest.mark.postgres
def test_postgres_json_round_trip() -> None:
    url = os.environ.get("SKILLGRAPH_TEST_DATABASE_URL", "")
    if not url.startswith("postgresql"):
        pytest.skip("PostgreSQL not configured")
    engine = make_engine(url)
    try:
        with engine.connect() as connection:
            assert connection.dialect.name == "postgresql"
            value = connection.execute(text("SELECT CAST('[\"Postgres\"]' AS json)")).scalar_one()
        assert "Postgres" in str(value)
    finally:
        engine.dispose()
