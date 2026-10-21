"""Fault injection around cyclic ontology and invalid edges."""

from __future__ import annotations

from app.domain.paths import build_learning_path
from app.domain.scoring import score_profile_against_role
from app.domain.types import ProfileSkillState, RelatedEdge, Requirement, SkillRecord
from fastapi.testclient import TestClient


def test_api_rejects_self_edge_and_invalid_type(client: TestClient) -> None:
    sql = next(row["id"] for row in client.get("/api/skills").json() if row["canonical_name"] == "SQL")
    self_edge = client.post(
        "/api/relations",
        json={
            "source_skill_id": sql,
            "target_skill_id": sql,
            "relation_type": "related",
            "weight": 0.5,
        },
    )
    assert self_edge.status_code == 400
    assert self_edge.json()["code"] == "bad_relation"

    invalid = client.post(
        "/api/relations",
        json={
            "source_skill_id": sql,
            "target_skill_id": next(
                row["id"] for row in client.get("/api/skills").json() if row["canonical_name"] == "Git"
            ),
            "relation_type": "implies",
            "weight": 0.5,
        },
    )
    # Pydantic Literal rejects unknown types before the handler (422).
    # Domain layer also rejects via invalid_edge_type when called directly.
    assert invalid.status_code in {400, 422}
    if invalid.status_code == 400:
        assert invalid.json()["code"] == "invalid_edge_type"


def test_alias_collision_rejected_on_create(client: TestClient) -> None:
    conflict = client.post(
        "/api/skills",
        json={"canonical_name": "Collision Probe", "category": "data", "aliases": ["Postgres"]},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "alias_collision"


def test_injected_prerequisite_cycle_surfaces_in_quality_and_path(client: TestClient) -> None:
    skills = {row["canonical_name"]: row["id"] for row in client.get("/api/skills").json()}
    a = client.post(
        "/api/skills",
        json={"canonical_name": "Fault Cycle A", "category": "legacy", "aliases": []},
    ).json()["id"]
    b = client.post(
        "/api/skills",
        json={"canonical_name": "Fault Cycle B", "category": "legacy", "aliases": []},
    ).json()["id"]
    for source, target in ((a, b), (b, a)):
        response = client.post(
            "/api/relations",
            json={
                "source_skill_id": source,
                "target_skill_id": target,
                "relation_type": "prerequisite",
                "weight": 1.0,
                "provenance": "fault-injection",
            },
        )
        assert response.status_code == 201

    quality = client.get("/api/ontology/quality").json()
    assert any(
        "Fault Cycle A" in cycle and "Fault Cycle B" in cycle
        for cycle in quality["prerequisite_cycles"]
    )

    path = build_learning_path(
        gap_reasons={a: "mandatory_gap", b: "mandatory_gap"},
        possessed_skill_ids=set(),
        prerequisite_edges=[(a, b), (b, a)],
        skill_names={a: "Fault Cycle A", b: "Fault Cycle B", skills["SQL"]: "SQL"},
    )
    assert path["cycle_free"] is False
    assert path["ordered_steps"] == []


def test_related_soft_credit_never_satisfies_mandatory_under_faulty_graph() -> None:
    skills = {
        1: SkillRecord(1, "dbt", (), "data"),
        2: SkillRecord(2, "SQL", (), "data"),
    }
    # Extreme related weight still cannot satisfy mandatory.
    related = {1: [RelatedEdge(other_skill_id=2, relation_type="related", weight=1.0)]}
    result = score_profile_against_role(
        requirements=[Requirement(1, 3, 5, True)],
        profile_skills=[ProfileSkillState(2, 5, "SQL")],
        skills=skills,
        related_index=related,
    )
    assert result.requirements[0].match_type == "related"
    assert result.requirements[0].mandatory_status == "missing"
    assert result.mandatory_satisfied is False
    assert result.missing_mandatories
    assert result.missing_mandatories[0]["skill_name"] == "dbt"
