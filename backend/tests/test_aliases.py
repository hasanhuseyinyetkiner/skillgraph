import pytest
from app.domain.aliases import build_alias_index, normalize_alias, resolve_skill_id


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("PostgreSQL", "postgresql"),
        ("  Postgres ", "postgres"),
        ("Node.js", "node js"),
        ("C#", "c#"),
        ("C++", "c++"),
        ("A/B Testing", "a b testing"),
        ("scikit-learn", "scikit learn"),
        ("Power BI", "power bi"),
        ("CI/CD", "ci cd"),
    ],
)
def test_normalize_alias(raw: str, expected: str) -> None:
    assert normalize_alias(raw) == expected


def test_alias_index_resolves_postgres_and_rejects_collisions() -> None:
    index = build_alias_index([(1, "PostgreSQL", ("Postgres", "Postgre SQL"))])
    assert resolve_skill_id("Postgres", index) == 1
    assert resolve_skill_id("postgresql", index) == 1
    assert resolve_skill_id("mysql", index) is None
    with pytest.raises(ValueError, match="collision"):
        build_alias_index(
            [
                (1, "PostgreSQL", ("Postgres",)),
                (2, "Other", ("postgres",)),
            ]
        )
