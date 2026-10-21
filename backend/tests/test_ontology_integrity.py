"""Ontology integrity regression: aliases, edges, orphans, cycles, hierarchy."""

from __future__ import annotations

from app.domain.ontology_integrity import (
    audit_ontology,
    find_alias_collisions,
    find_broader_narrower_inconsistencies,
    find_duplicate_aliases_within_skills,
    find_invalid_edge_types,
    find_orphan_skills,
    find_self_edges,
)
from fastapi.testclient import TestClient


def test_duplicate_aliases_within_skill_detected() -> None:
    findings = find_duplicate_aliases_within_skills(
        [(1, "PostgreSQL", ("Postgres", "postgres", "PG"))]
    )
    assert findings
    assert "postgres" in findings[0]["duplicate_tokens"]


def test_alias_collisions_across_skills() -> None:
    collisions = find_alias_collisions(
        [
            (1, "PostgreSQL", ("Postgres",)),
            (2, "Other DB", ("postgres",)),
        ]
    )
    assert collisions
    assert collisions[0]["token"] == "postgres"
    assert len(collisions[0]["skills"]) == 2


def test_self_edges_and_invalid_types() -> None:
    relations = [(1, 1, "related"), (1, 2, "not_a_type"), (1, 2, "prerequisite")]
    assert find_self_edges(relations) == [
        {"source_skill_id": 1, "target_skill_id": 1, "relation_type": "related"}
    ]
    assert find_invalid_edge_types(relations) == [
        {"source_skill_id": 1, "target_skill_id": 2, "relation_type": "not_a_type"}
    ]


def test_orphans_exclude_referenced_and_connected() -> None:
    orphans = find_orphan_skills(
        skill_ids={1, 2, 3, 4},
        relations=[(1, 2, "related")],
        referenced_skill_ids={3},
    )
    assert orphans == [4]


def test_broader_narrower_conflicts_and_missing_inverses() -> None:
    # A broader B without inverse narrower -> warning only
    hierarchy = find_broader_narrower_inconsistencies([(1, 2, "broader")])
    assert hierarchy["conflicts"] == []
    assert hierarchy["missing_narrower_inverses"]

    # Same pair both broader and narrower in one direction -> conflict
    conflicted = find_broader_narrower_inconsistencies(
        [(1, 2, "broader"), (1, 2, "narrower")]
    )
    assert any(item["kind"] == "same_direction_broader_and_narrower" for item in conflicted["conflicts"])

    mutual = find_broader_narrower_inconsistencies(
        [(1, 2, "broader"), (2, 1, "broader")]
    )
    assert any(item["kind"] == "mutual_broader" for item in mutual["conflicts"])


def test_audit_reports_cycle() -> None:
    report = audit_ontology(
        skills=[
            (1, "A", ()),
            (2, "B", ()),
            (3, "C", ()),
        ],
        relations=[(1, 2, "prerequisite"), (2, 3, "prerequisite"), (3, 1, "prerequisite")],
        prerequisite_edges=[(1, 2), (2, 3), (3, 1)],
        referenced_skill_ids=set(),
    )
    assert report["prerequisite_cycles"]
    assert report["self_edges"] == []
    assert report["alias_collisions"] == []


def test_seeded_ontology_quality_exposes_integrity_fields(client: TestClient) -> None:
    quality = client.get("/api/ontology/quality").json()
    assert "alias_collisions" in quality
    assert "duplicate_aliases_within_skills" in quality
    assert "self_edges" in quality
    assert "invalid_edge_types" in quality
    assert "orphan_skill_ids" in quality
    assert "broader_narrower_conflicts" in quality
    assert "missing_narrower_inverses_count" in quality
    assert quality["alias_collisions"] == []
    assert quality["self_edges"] == []
    assert quality["invalid_edge_types"] == []
    assert quality["broader_narrower_conflicts"] == []
    assert any("Legacy SOAP" in cycle for cycle in quality["prerequisite_cycles"])
    # Seed stores broader without inverse narrower — informational, not a conflict.
    assert quality["missing_narrower_inverses_count"] >= 1


def test_graph_version_bumps_atomically_with_relation(client: TestClient) -> None:
    before = client.get("/api/graph").json()["graph_version"]
    skills = {row["canonical_name"]: row["id"] for row in client.get("/api/skills").json()}
    created = client.post(
        "/api/skills",
        json={"canonical_name": "Integrity Probe", "category": "data", "aliases": ["integ probe"]},
    )
    assert created.status_code == 201
    mid = created.json()["graph_version"]
    assert mid == before + 1
    relation = client.post(
        "/api/relations",
        json={
            "source_skill_id": skills["SQL"],
            "target_skill_id": created.json()["id"],
            "relation_type": "related",
            "weight": 0.4,
            "provenance": "integrity-test",
        },
    )
    assert relation.status_code == 201
    assert relation.json()["graph_version"] == mid + 1
    assert client.get("/api/graph").json()["graph_version"] == mid + 1
