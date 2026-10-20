from fastapi.testclient import TestClient


def test_graph_version_visible_across_two_app_instances(two_clients: tuple[TestClient, TestClient]) -> None:
    client_a, client_b = two_clients
    version_a = client_a.get("/api/graph").json()["graph_version"]
    version_b = client_b.get("/api/graph").json()["graph_version"]
    assert version_a == version_b
    sql_id = next(row["id"] for row in client_a.get("/api/skills").json() if row["canonical_name"] == "SQL")
    created = client_a.post(
        "/api/skills",
        json={"canonical_name": "Edge Probe Skill", "category": "data", "aliases": ["edge probe"]},
    )
    assert created.status_code == 201
    relation = client_a.post(
        "/api/relations",
        json={
            "source_skill_id": sql_id,
            "target_skill_id": created.json()["id"],
            "relation_type": "related",
            "weight": 0.4,
            "provenance": "test",
        },
    )
    assert relation.status_code == 201
    graph_a = client_a.get("/api/graph").json()
    graph_b = client_b.get("/api/graph").json()
    assert graph_a["graph_version"] == version_a + 2
    assert graph_b["graph_version"] == graph_a["graph_version"]
    edge = (
        f"skill:{sql_id}",
        f"skill:{created.json()['id']}",
        "related",
    )
    assert edge in {(item["source"], item["target"], item["type"]) for item in graph_b["edges"]}
    demo = client_b.get("/api/profiles/demo").json()
    role_id = next(row["id"] for row in client_b.get("/api/roles").json() if row["title"] == "Data Analyst")
    recommendation = client_b.post(
        "/api/recommendations",
        json={"profile_id": demo["id"], "role_id": role_id},
    ).json()
    assert recommendation["graph_version"] == graph_b["graph_version"]
    assert recommendation["method_version"] == "skg-baseline-1.0.0"
