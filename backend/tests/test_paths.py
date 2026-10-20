from app.domain.paths import build_learning_path


def names(path: dict) -> list[str]:
    return [step["skill_name"] for step in path["ordered_steps"]]


def test_chain_orders_prerequisites_and_skips_possessed() -> None:
    edges = [(1, 2), (2, 3)]
    labels = {1: "SQL", 2: "Data Modeling", 3: "dbt"}
    full = build_learning_path(
        gap_reasons={3: "mandatory_gap"},
        possessed_skill_ids=set(),
        prerequisite_edges=edges,
        skill_names=labels,
    )
    assert names(full) == ["SQL", "Data Modeling", "dbt"]
    assert full["cycle_free"] is True
    pruned = build_learning_path(
        gap_reasons={3: "mandatory_gap"},
        possessed_skill_ids={1},
        prerequisite_edges=edges,
        skill_names=labels,
    )
    assert names(pruned) == ["Data Modeling", "dbt"]


def test_cycle_is_reported_and_not_linearized() -> None:
    path = build_learning_path(
        gap_reasons={1: "mandatory_gap", 2: "mandatory_gap", 3: "mandatory_gap"},
        possessed_skill_ids=set(),
        prerequisite_edges=[(1, 2), (2, 3), (3, 1)],
        skill_names={1: "Legacy SOAP", 2: "Legacy XML Mapping", 3: "Legacy Queue Bridge"},
    )
    assert path["ordered_steps"] == []
    assert path["cycle_free"] is False
    assert path["cycle_blocks"][0]["skill_names"] == [
        "Legacy Queue Bridge",
        "Legacy SOAP",
        "Legacy XML Mapping",
    ]
    assert "will not invent" in path["cycle_blocks"][0]["explanation"]


def test_empty_gaps() -> None:
    path = build_learning_path(
        gap_reasons={},
        possessed_skill_ids=set(),
        prerequisite_edges=[],
        skill_names={},
    )
    assert path["timeline"] == []
    assert path["cycle_free"] is True


def test_diamond_keeps_prerequisites_ahead() -> None:
    path = build_learning_path(
        gap_reasons={3: "mandatory_gap"},
        possessed_skill_ids=set(),
        prerequisite_edges=[(1, 3), (2, 3)],
        skill_names={1: "SQL", 2: "Git", 3: "dbt"},
    )
    ordered = names(path)
    assert ordered.index("SQL") < ordered.index("dbt")
    assert ordered.index("Git") < ordered.index("dbt")
    assert path["cycle_free"] is True
