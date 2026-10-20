"""Ranking metrics and the synthetic gold-fixture evaluation."""

from __future__ import annotations

import math

from app.domain.scoring import overlap_baseline_score, score_profile_against_role
from app.domain.types import ProfileSkillState, Requirement, SkillRecord, Weights


def dcg(relevances: list[float]) -> float:
    return sum(relevance / math.log2(index + 2) for index, relevance in enumerate(relevances))


def ndcg_at_k(ranked_relevances: list[float], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    ideal = sorted(ranked_relevances, reverse=True)
    ideal_gain = dcg(ideal[:k])
    if ideal_gain == 0:
        return 1.0
    return dcg(ranked_relevances[:k]) / ideal_gain


def precision_at_k(ranked_relevances: list[float], k: int) -> float:
    if k <= 0:
        raise ValueError("k must be positive")
    window = ranked_relevances[:k]
    if not window:
        return 0.0
    return sum(1 for relevance in window if relevance > 0) / len(window)


def _macro(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def evaluate_rankers(
    *,
    profiles: list[dict[str, object]],
    roles: dict[str, list[Requirement]],
    skills: dict[int, SkillRecord],
    skills_by_name: dict[str, SkillRecord],
    related_index: dict[int, list],
    k_values: tuple[int, ...] = (3, 5),
) -> dict[str, object]:
    """Compare overlap baseline vs graph-augmented scoring on hand-labeled fixtures.

    Each profile names a candidate set. Unlabeled roles are excluded rather than
    treated as invented zeros. Relevance grades are the fixture's grades, not
    the scorer's output.
    """

    per_profile: list[dict[str, object]] = []
    buckets: dict[str, dict[str, list[float]]] = {
        "overlap": {f"precision_at_{k}": [] for k in k_values}
        | {f"ndcg_at_{k}": [] for k in k_values},
        "graph": {f"precision_at_{k}": [] for k in k_values}
        | {f"ndcg_at_{k}": [] for k in k_values},
    }

    for profile in profiles:
        labels: dict[str, int] = profile["labels"]  # type: ignore[assignment]
        raw_skills: list[tuple[str, int | None, str]] = profile["skills"]  # type: ignore[assignment]
        profile_skills = [
            ProfileSkillState(
                skill_id=skills_by_name[name].id,
                level=level,
                asserted_label=label,
            )
            for name, level, label in raw_skills
        ]
        ranking_rows: list[dict[str, object]] = []
        for role_title, relevance in labels.items():
            requirements = roles[role_title]
            graph_score = score_profile_against_role(
                requirements=requirements,
                profile_skills=profile_skills,
                skills=skills,
                related_index=related_index,
                weights=Weights(),
            )
            overlap = overlap_baseline_score(
                requirements=requirements,
                profile_skills=profile_skills,
                skills=skills,
            )
            ranking_rows.append(
                {
                    "role": role_title,
                    "relevance": relevance,
                    "graph": graph_score.coverage,
                    "overlap": overlap,
                }
            )

        def order(method: str, rows: list[dict[str, object]] = ranking_rows) -> list[float]:
            ordered = sorted(rows, key=lambda row: (-float(row[method]), str(row["role"])))
            return [float(row["relevance"]) for row in ordered]

        graph_rels = order("graph")
        overlap_rels = order("overlap")
        for method, rels in (("graph", graph_rels), ("overlap", overlap_rels)):
            for k in k_values:
                buckets[method][f"precision_at_{k}"].append(precision_at_k(rels, k))
                buckets[method][f"ndcg_at_{k}"].append(ndcg_at_k(rels, k))
        per_profile.append({"profile": profile["id"], "roles": ranking_rows})

    def summarize(method: str) -> dict[str, float]:
        return {key: _macro(values) for key, values in buckets[method].items()}

    return {
        "k_values": list(k_values),
        "profile_count": len(profiles),
        "candidate_policy": "hand-labeled candidate set per profile; unlabeled roles are excluded",
        "label_policy": "grades are hand-assigned from the fixture rules, not copied from the scorer",
        "overlap": summarize("overlap"),
        "graph": summarize("graph"),
        "per_profile": per_profile,
    }
