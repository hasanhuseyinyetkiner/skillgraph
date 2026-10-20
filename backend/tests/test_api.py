import json
import time

from fastapi.testclient import TestClient


def skill_id(client: TestClient, name: str) -> int:
    for row in client.get("/api/skills").json():
        if row["canonical_name"] == name:
            return int(row["id"])
    raise AssertionError(name)


def role_id(client: TestClient, title: str) -> int:
    for row in client.get("/api/roles").json():
        if row["title"] == title:
            return int(row["id"])
    raise AssertionError(title)


def test_health_ready_and_seed_counts(client: TestClient) -> None:
    assert client.get("/health").json()["status"] == "ok"
    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["graph_version"] >= 1
    meta = client.get("/api/meta").json()
    assert meta["app_env"] == "test"
    assert meta["banner"] is None
    assert meta["method_version"] == "skg-baseline-1.0.0"
    assert meta["weights"]["semantic_similarity"] == 0
    quality = client.get("/api/ontology/quality").json()
    assert quality["skill_count"] >= 80
    assert quality["role_count"] >= 20
    assert quality["resource_count"] >= 30
    assert any("Legacy SOAP" in cycle for cycle in quality["prerequisite_cycles"])
    graph = client.get("/api/graph", params={"family": "Data & Analytics"}).json()
    labels = {node["label"] for node in graph["nodes"]}
    assert "SQL" in labels
    assert "Analytics Engineer" in labels
    assert graph["graph_version"] == ready.json()["graph_version"]


def test_demo_fit_breakdown_path_and_skill_edit(client: TestClient) -> None:
    demo = client.get("/api/profiles/demo").json()
    assert demo["display_name"] == "Avery Chen"
    assert demo["synthetic"] is True
    assert any(row["asserted_label"] == "Postgres" for row in demo["skills"])
    version_before = client.get("/api/graph").json()["graph_version"]
    analytics = role_id(client, "Analytics Engineer")
    recommendation = client.post(
        "/api/recommendations",
        json={"profile_id": demo["id"], "role_id": analytics},
    ).json()
    rows = {row["skill_name"]: row for row in recommendation["requirements"]}
    assert recommendation["fit_index_label"] == "Exploratory fit index"
    assert "not a probability of getting a job" in recommendation["disclaimer"]
    assert recommendation["method_version"] == "skg-baseline-1.0.0"
    assert recommendation["graph_version"] == version_before
    assert rows["PostgreSQL"]["match_type"] == "validated_synonym"
    assert rows["PostgreSQL"]["mandatory_status"] == "satisfied"
    assert rows["dbt"]["mandatory"] is True
    assert rows["dbt"]["mandatory_status"] == "missing"
    assert rows["Git"]["mandatory_status"] == "level_gap"
    assert rows["Data Modeling"]["match_type"] == "related"
    assert rows["Data Modeling"]["mandatory_status"] == "missing"
    assert recommendation["mandatory_satisfied"] is False
    assert recommendation["trace_id"] > 0
    assert sum(recommendation["match_type_counts"].values()) == len(recommendation["requirements"])

    path = client.post(
        "/api/learning-paths",
        json={"profile_id": demo["id"], "role_id": analytics},
    ).json()
    ordered = [step["skill_name"] for step in path["ordered_steps"]]
    assert path["cycle_free"] is True
    assert ordered.index("Data Modeling") < ordered.index("dbt")
    assert any(step["skill_name"] == "dbt" and step["resources"] for step in path["ordered_steps"])
    assert "Missing estimates are counted" in path["duration_note"]

    legacy = client.post(
        "/api/learning-paths",
        json={"profile_id": demo["id"], "role_id": role_id(client, "Legacy Integration Engineer")},
    ).json()
    assert legacy["cycle_free"] is False
    assert any("Legacy SOAP" in block["skill_names"] for block in legacy["cycle_blocks"])
    assert legacy["ordered_steps"] == [] or all(
        step["skill_name"] != "Legacy SOAP" for step in legacy["ordered_steps"]
    )

    before = recommendation["fit_index"]
    client.post(
        f"/api/profiles/{demo['id']}/skills",
        json={"skill_id": skill_id(client, "dbt"), "self_assessed_level": 4, "asserted_label": "dbt"},
    )
    assert client.get("/api/graph").json()["graph_version"] == version_before
    after = client.post(
        "/api/recommendations",
        json={"profile_id": demo["id"], "role_id": analytics},
    ).json()
    after_rows = {row["skill_name"]: row for row in after["requirements"]}
    assert after["fit_index"] > before
    assert after_rows["dbt"]["mandatory_status"] == "satisfied"
    assert after["graph_version"] == version_before


def test_empty_profile_unknown_level_and_csv(client: TestClient) -> None:
    created = client.post("/api/profiles", json={"display_name": "Empty Example"}).json()
    analyst = role_id(client, "Data Analyst")
    empty = client.post(
        "/api/recommendations",
        json={"profile_id": created["id"], "role_id": analyst},
    ).json()
    assert empty["fit_index"] == 0
    assert empty["mandatory_satisfied"] is False
    assert all(row["match_type"] == "unlisted" for row in empty["requirements"])

    sql = skill_id(client, "SQL")
    client.post(
        f"/api/profiles/{created['id']}/skills",
        json={"skill_id": sql, "self_assessed_level": None, "asserted_label": "SQL"},
    )
    unknown = client.post(
        "/api/recommendations",
        json={"profile_id": created["id"], "role_id": analyst},
    ).json()
    sql_row = next(row for row in unknown["requirements"] if row["skill_name"] == "SQL")
    assert sql_row["presence"] == "unknown_level"
    assert sql_row["mandatory_status"] == "unconfirmed"

    rejected = client.post(
        "/api/recommendations",
        json={
            "profile_id": created["id"],
            "role_id": analyst,
            "weights": {"semantic_similarity": 0.8},
        },
    )
    assert rejected.status_code == 400

    payload = b"skill,level\nPostgres,4\nNot A Skill,2\nSQL,5\n"
    preview = client.post(
        f"/api/profiles/{created['id']}/import",
        params={"mode": "preview"},
        files={"file": ("skills.csv", payload, "text/csv")},
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["unknown_count"] == 1
    assert any(row["match"] == "alias" and row["canonical_name"] == "PostgreSQL" for row in body["rows"])
    bad = client.post(
        f"/api/profiles/{created['id']}/import",
        files={"file": ("notes.txt", payload, "text/plain")},
    )
    assert bad.status_code == 415

    exported = client.get(f"/api/profiles/{created['id']}/export").json()
    assert exported["synthetic"] is True
    client.delete(f"/api/profiles/{created['id']}")
    assert client.get(f"/api/profiles/{created['id']}").status_code == 404


def test_compare_and_summary_budget(client: TestClient) -> None:
    demo = client.get("/api/profiles/demo").json()
    started = time.perf_counter()
    summary = client.get(f"/api/profiles/{demo['id']}/summary")
    elapsed = time.perf_counter() - started
    assert summary.status_code == 200
    assert elapsed < 2
    print(f"SUMMARY_SECONDS {elapsed:.4f}")
    body = summary.json()
    assert body["skill_count"] == 14
    assert body["ontology"]["skill_count"] >= 80
    assert body["role_fits"]
    compared = client.post(
        "/api/recommendations/compare",
        json={
            "profile_id": demo["id"],
            "role_a_id": role_id(client, "Data Analyst"),
            "role_b_id": role_id(client, "Analytics Engineer"),
        },
    ).json()
    assert compared["role_a"]["role"]["title"] == "Data Analyst"
    assert compared["role_b"]["mandatory_satisfied"] is False
    assert "SQL" in compared["shared_identity_skills"]
    assert "dbt" in compared["only_b_mandatory_gaps"]


def test_evaluation_reports_measured_metrics(client: TestClient) -> None:
    report = client.get("/api/evaluation").json()
    print("EVAL_METRICS " + json.dumps({"overlap": report["overlap"], "graph": report["graph"]}))
    assert report["profile_count"] == 5
    expected_keys = {
        "precision_at_3",
        "precision_at_5",
        "recall_at_3",
        "recall_at_5",
        "ndcg_at_3",
        "ndcg_at_5",
    }
    for method in ("overlap", "graph"):
        assert set(report[method]) == expected_keys
        for key, value in report[method].items():
            assert 0 <= value <= 1, key
    synonym = next(item for item in report["per_profile"] if item["profile"] == "synonym_specialist")
    backend = next(item for item in synonym["roles"] if item["role"] == "Backend Engineer")
    assert backend["graph"] > backend["overlap"]


def test_demo_reset_restores_postgres_alias(client: TestClient) -> None:
    demo = client.get("/api/profiles/demo").json()
    client.delete(f"/api/profiles/{demo['id']}/skills/{skill_id(client, 'SQL')}")
    reset = client.post("/api/profiles/demo/reset").json()
    assert any(row["canonical_name"] == "SQL" for row in reset["skills"])
    assert any(row["asserted_label"] == "Postgres" for row in reset["skills"])
