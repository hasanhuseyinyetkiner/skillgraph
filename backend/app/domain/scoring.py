"""Deterministic requirement matching.

The fit index is the importance-weighted sum of per-requirement credits.
Exact, validated-synonym, and related credits are the only terms in the index.
Semantic similarity is accepted as an optional display signal and is ignored
by the arithmetic. Mandatory status is a separate gate.
"""

from __future__ import annotations

from app.domain.aliases import normalize_alias
from app.domain.constants import UNKNOWN_LEVEL_FACTOR
from app.domain.types import (
    ProfileSkillState,
    RelatedEdge,
    Requirement,
    RequirementScore,
    ScoreResult,
    SkillRecord,
    Weights,
)


def level_factor(level: int | None, target: int) -> tuple[float, str]:
    if level is None:
        return UNKNOWN_LEVEL_FACTOR, "unknown_level"
    if level <= 0:
        return 0.0, "absent"
    if target <= 0 or level >= target:
        return 1.0, "met"
    return level / target, "level_gap"


def _identity_match_type(profile_skill: ProfileSkillState, skill: SkillRecord) -> str:
    label = normalize_alias(profile_skill.asserted_label or "")
    canonical = normalize_alias(skill.canonical_name)
    alias_tokens = {normalize_alias(alias) for alias in skill.aliases}
    if label and label != canonical and label in alias_tokens:
        return "validated_synonym"
    return "exact"


def _best_related(
    requirement: Requirement,
    profile_by_skill: dict[int, ProfileSkillState],
    related_index: dict[int, list[RelatedEdge]],
    skills: dict[int, SkillRecord],
) -> tuple[ProfileSkillState, RelatedEdge, float, str] | None:
    best: tuple[ProfileSkillState, RelatedEdge, float, str] | None = None
    for edge in related_index.get(requirement.skill_id, []):
        other = profile_by_skill.get(edge.other_skill_id)
        if other is None or (other.level is not None and other.level <= 0):
            continue
        factor, status = level_factor(other.level, requirement.target_level)
        score = edge.weight * factor
        if best is None or score > best[2]:
            best = (other, edge, factor, status)
    return best


def _mandatory_status(mandatory: bool, match_type: str, level_status: str) -> str:
    if not mandatory:
        return "not_applicable"
    if match_type in {"exact", "validated_synonym"} and level_status == "met":
        return "satisfied"
    if match_type in {"exact", "validated_synonym"} and level_status == "unknown_level":
        return "unconfirmed"
    if match_type in {"exact", "validated_synonym"} and level_status == "level_gap":
        return "level_gap"
    return "missing"


def score_profile_against_role(
    *,
    requirements: list[Requirement],
    profile_skills: list[ProfileSkillState],
    skills: dict[int, SkillRecord],
    related_index: dict[int, list[RelatedEdge]],
    weights: Weights | None = None,
    semantic_scores: dict[int, float] | None = None,
    semantic_reason: str = "embeddings_disabled",
) -> ScoreResult:
    active = weights or Weights()
    active.validate()
    profile_by_skill = {item.skill_id: item for item in profile_skills}
    rows: list[RequirementScore] = []

    for requirement in requirements:
        skill = skills[requirement.skill_id]
        profile_skill = profile_by_skill.get(requirement.skill_id)
        notes: list[str] = []
        matched_via: dict[str, object] | None = None
        asserted: str | None = None
        semantic_value = None if semantic_scores is None else semantic_scores.get(requirement.skill_id)

        explicit_absence = (
            profile_skill is not None and profile_skill.level is not None and profile_skill.level <= 0
        )
        if profile_skill is not None and not explicit_absence:
            match_type = _identity_match_type(profile_skill, skill)
            factor, level_status = level_factor(profile_skill.level, requirement.target_level)
            coefficient = (
                active.exact_match if match_type == "exact" else active.validated_synonym
            )
            credit = coefficient * factor
            presence = "unknown_level" if profile_skill.level is None else "matched"
            profile_level = profile_skill.level
            asserted = profile_skill.asserted_label or skill.canonical_name
            if match_type == "validated_synonym":
                notes.append(f"Asserted label '{asserted}' is a stored alias.")
            if profile_skill.level is None:
                notes.append(
                    "Level is unknown. The skill is not treated as absent, "
                    "and a mandatory requirement stays unconfirmed."
                )
        else:
            related = _best_related(requirement, profile_by_skill, related_index, skills)
            if related is not None:
                other, edge, factor, level_status = related
                other_skill = skills[other.skill_id]
                match_type = "related"
                presence = "related"
                credit = active.related_skill * edge.weight * factor
                profile_level = other.level
                asserted = other.asserted_label
                level_status = level_status
                matched_via = {
                    "skill_id": other.skill_id,
                    "skill_name": other_skill.canonical_name,
                    "relation_type": edge.relation_type,
                    "weight": edge.weight,
                    "asserted_label": other.asserted_label,
                }
                if explicit_absence:
                    notes.append(
                        "The required skill is explicitly absent. "
                        "Related credit does not satisfy a mandatory requirement."
                    )
                else:
                    notes.append(
                        "Skill is unlisted, which is unknown rather than definite absence. "
                        "Related credit does not satisfy a mandatory requirement."
                    )
            elif explicit_absence:
                match_type = "absent"
                presence = "absent"
                factor = 0.0
                level_status = "absent"
                credit = 0.0
                profile_level = 0
                asserted = profile_skill.asserted_label if profile_skill else None
                notes.append("Profile lists this skill at level 0 (explicit absence).")
            else:
                match_type = "unlisted"
                presence = "unlisted"
                factor = 0.0
                level_status = "unlisted"
                credit = 0.0
                profile_level = None
                notes.append("Skill is unlisted. That is unknown, not definite absence.")

        if semantic_value is not None:
            notes.append("Semantic similarity is display-only and does not change the fit index.")

        rows.append(
            RequirementScore(
                skill_id=requirement.skill_id,
                skill_name=skill.canonical_name,
                category=skill.category,
                mandatory=requirement.mandatory,
                importance=requirement.importance,
                target_level=requirement.target_level,
                match_type=match_type,
                presence=presence,
                level_status=level_status,
                profile_level=profile_level,
                asserted_label=asserted,
                level_factor=factor,
                credit=credit,
                mandatory_status=_mandatory_status(
                    requirement.mandatory, match_type, level_status
                ),
                matched_via=matched_via,
                semantic_similarity=semantic_value,
                notes=notes,
            )
        )

    total_importance = sum(row.importance for row in rows)
    if total_importance <= 0:
        exact = synonym = related = 0.0
    else:
        exact = (
            sum(row.importance * row.credit for row in rows if row.match_type == "exact")
            / total_importance
        )
        synonym = (
            sum(
                row.importance * row.credit
                for row in rows
                if row.match_type == "validated_synonym"
            )
            / total_importance
        )
        related = (
            sum(row.importance * row.credit for row in rows if row.match_type == "related")
            / total_importance
        )
    coverage = exact + synonym + related
    identity_factors = [
        row.level_factor
        for row in rows
        if row.match_type in {"exact", "validated_synonym"} and row.presence != "absent"
    ]
    level_adequacy = (
        sum(identity_factors) / len(identity_factors) if identity_factors else 0.0
    )
    semantic_values = [row.semantic_similarity for row in rows if row.semantic_similarity is not None]
    semantic_mean = sum(semantic_values) / len(semantic_values) if semantic_values else None
    mandatory_rows = [row for row in rows if row.mandatory]
    satisfied = [row for row in mandatory_rows if row.mandatory_status == "satisfied"]
    components: dict[str, object] = {
        "exact_match": {"contribution": exact, "in_fit_index": True},
        "validated_synonym": {"contribution": synonym, "in_fit_index": True},
        "related_skill": {"contribution": related, "in_fit_index": True},
        "level_adequacy": {
            "value": level_adequacy,
            "in_fit_index": False,
            "note": "Average level factor on identity matches. Already applied inside credits.",
        },
        "semantic_similarity": {
            "value": semantic_mean,
            "in_fit_index": False,
            "reason": semantic_reason if semantic_mean is None else "display_only",
        },
    }
    return ScoreResult(
        fit_index=round(coverage * 100, 1),
        coverage=coverage,
        weights=active,
        requirements=rows,
        components=components,
        mandatory_satisfied=all(row.mandatory_status == "satisfied" for row in mandatory_rows),
        mandatory_total=len(mandatory_rows),
        mandatory_satisfied_count=len(satisfied),
        semantic_reason=semantic_reason if semantic_mean is None else "display_only",
    )


def overlap_baseline_score(
    *,
    requirements: list[Requirement],
    profile_skills: list[ProfileSkillState],
    skills: dict[int, SkillRecord],
) -> float:
    """Name-overlap baseline: canonical label only, no alias table and no graph."""

    if not requirements:
        return 0.0
    hits = 0
    for requirement in requirements:
        canonical = normalize_alias(skills[requirement.skill_id].canonical_name)
        for profile_skill in profile_skills:
            if profile_skill.level is not None and profile_skill.level <= 0:
                continue
            if normalize_alias(profile_skill.asserted_label or "") == canonical:
                hits += 1
                break
    return hits / len(requirements)
