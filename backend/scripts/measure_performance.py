"""Measure path/fit latency against a seeded SQLite demo.

Usage (from backend/):
  uv run python scripts/measure_performance.py

Prints JSON. Local wall-clock only — not a remote SLA claim.
"""

from __future__ import annotations

import json
import statistics
import tempfile
import time
from pathlib import Path

from app.db import make_engine, run_migrations
from app.domain.gold import GOLD_PROFILES
from app.domain.metrics import evaluate_rankers
from app.domain.paths import build_learning_path
from app.domain.scoring import score_profile_against_role
from app.domain.types import ProfileSkillState, Weights
from app.main import create_app
from app.models import Profile
from app.seed import seed_ontology
from app.services.catalog import load_snapshot, ontology_quality, recommend
from app.settings import Settings
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker


def _percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((pct / 100) * (len(ordered) - 1)))))
    return ordered[index]


def _time_many(fn, repeats: int) -> dict[str, float]:
    samples: list[float] = []
    for _ in range(repeats):
        started = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - started) * 1000)
    return {
        "n": float(repeats),
        "mean_ms": round(statistics.fmean(samples), 3),
        "median_ms": round(statistics.median(samples), 3),
        "p95_ms": round(_percentile(samples, 95), 3),
        "min_ms": round(min(samples), 3),
        "max_ms": round(max(samples), 3),
    }


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "perf.db"
        url = f"sqlite:///{db_path.as_posix()}"
        run_migrations(url)
        engine = make_engine(url)
        factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)
        with factory() as session:
            seed_ontology(session)
            snapshot = load_snapshot(session)
            demo = session.scalars(select(Profile).where(Profile.slug == "demo")).one()
            profile_id = int(demo.id)

        demo_skills = next(p for p in GOLD_PROFILES if p["id"] == "data_analyst_demo")
        profile_states = [
            ProfileSkillState(
                skill_id=snapshot.skills_by_name[name].id,
                level=level,
                asserted_label=label,
            )
            for name, level, label in demo_skills["skills"]  # type: ignore[misc]
        ]
        role = next(item for item in snapshot.roles.values() if item.title == "Analytics Engineer")

        def score_once() -> None:
            score_profile_against_role(
                requirements=role.requirements,
                profile_skills=profile_states,
                skills=snapshot.skills,
                related_index=snapshot.related_index,
                weights=Weights(),
            )

        score_stats = _time_many(score_once, repeats=50)

        scored = score_profile_against_role(
            requirements=role.requirements,
            profile_skills=profile_states,
            skills=snapshot.skills,
            related_index=snapshot.related_index,
            weights=Weights(),
        )
        gap_reasons = {
            row.skill_id: row.mandatory_status
            for row in scored.requirements
            if row.mandatory_status != "satisfied"
        }
        possessed = {item.skill_id for item in profile_states}

        def path_once() -> None:
            build_learning_path(
                gap_reasons=gap_reasons,
                possessed_skill_ids=possessed,
                prerequisite_edges=list(snapshot.prerequisite_edges),
                skill_names={sid: skill.canonical_name for sid, skill in snapshot.skills.items()},
            )

        path_stats = _time_many(path_once, repeats=50)

        roles_map = {item.title: item.requirements for item in snapshot.roles.values()}

        def eval_once() -> None:
            evaluate_rankers(
                profiles=GOLD_PROFILES,
                roles=roles_map,
                skills=snapshot.skills,
                skills_by_name=snapshot.skills_by_name,
                related_index=snapshot.related_index,
            )

        eval_stats = _time_many(eval_once, repeats=10)
        quality_stats = _time_many(lambda: ontology_quality(snapshot), repeats=20)

        settings = Settings(
            app_env="test",
            database_url=url,
            host="127.0.0.1",
            port=8105,
            allow_network_bind=False,
            auto_seed=False,
            run_migrations=False,
            embeddings_enabled=False,
        )
        application = create_app(settings)
        cache = application.state.graph_cache
        session_factory = application.state.session_factory

        def recommend_once() -> None:
            recommend(
                session_factory,
                cache,
                settings,
                profile_id=profile_id,
                role_id=role.id,
                weights_payload=None,
            )

        recommend_stats = _time_many(recommend_once, repeats=25)

        payload = {
            "host": "local Windows / SQLite temp DB",
            "skill_count": len(snapshot.skills),
            "role_count": len(snapshot.roles),
            "relation_count": len(snapshot.relations),
            "gold_profile_count": len(GOLD_PROFILES),
            "measurements_ms": {
                "score_profile_against_role_analytics_engineer": score_stats,
                "build_learning_path_analytics_engineer": path_stats,
                "evaluate_rankers_full_gold": eval_stats,
                "ontology_quality_audit": quality_stats,
                "recommend_api_stack_demo_analytics_engineer": recommend_stats,
            },
        }
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
