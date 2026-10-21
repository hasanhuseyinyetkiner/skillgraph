import pytest
from app.domain.constants import (
    FIT_INDEX_LABEL,
    METHOD_VERSION,
    SEMANTIC_COMPOSITE_WEIGHT,
    WEIGHTS_VERSION,
)
from app.domain.scoring import overlap_baseline_score, score_profile_against_role
from app.domain.types import ProfileSkillState, RelatedEdge, Requirement, SkillRecord, Weights


def skill(skill_id: int, name: str, aliases: tuple[str, ...] = ()) -> SkillRecord:
    return SkillRecord(id=skill_id, canonical_name=name, aliases=aliases, category="data")


def test_weight_invariants_and_perfect_exact_match() -> None:
    weights = Weights()
    assert weights.semantic_similarity == SEMANTIC_COMPOSITE_WEIGHT == 0
    assert weights.version_label == WEIGHTS_VERSION
    assert METHOD_VERSION == "skg-baseline-1.0.0"
    skills = {1: skill(1, "SQL")}
    result = score_profile_against_role(
        requirements=[Requirement(1, target_level=3, importance=5, mandatory=True)],
        profile_skills=[ProfileSkillState(1, 4, "SQL")],
        skills=skills,
        related_index={},
        weights=weights,
    )
    assert result.fit_index == 100
    assert result.coverage == pytest.approx(1)
    assert result.mandatory_satisfied is True
    assert result.as_dict()["fit_index_label"] == FIT_INDEX_LABEL
    components = result.components
    coverage = (
        components["exact_match"]["contribution"]
        + components["validated_synonym"]["contribution"]
        + components["related_skill"]["contribution"]
    )
    assert coverage == pytest.approx(result.coverage)
    assert components["semantic_similarity"]["in_fit_index"] is False


def test_synonym_scores_below_exact_and_overlap_misses_alias() -> None:
    skills = {1: skill(1, "PostgreSQL", ("Postgres",))}
    requirements = [Requirement(1, 3, 5, True)]
    profile = [ProfileSkillState(1, 4, "Postgres")]
    result = score_profile_against_role(
        requirements=requirements,
        profile_skills=profile,
        skills=skills,
        related_index={},
    )
    assert result.requirements[0].match_type == "validated_synonym"
    assert result.fit_index == pytest.approx(95)
    assert result.mandatory_satisfied is True
    assert overlap_baseline_score(requirements=requirements, profile_skills=profile, skills=skills) == 0


def test_mandatory_gap_is_not_hidden_by_related_or_semantic_scores() -> None:
    skills = {
        1: skill(1, "dbt"),
        2: skill(2, "SQL"),
    }
    related = {1: [RelatedEdge(other_skill_id=2, relation_type="related", weight=1.0)]}
    requirements = [
        Requirement(1, 3, 5, True),
        Requirement(2, 3, 1, False),
    ]
    profile = [ProfileSkillState(2, 5, "SQL")]
    plain = score_profile_against_role(
        requirements=requirements,
        profile_skills=profile,
        skills=skills,
        related_index=related,
    )
    inflated = score_profile_against_role(
        requirements=requirements,
        profile_skills=profile,
        skills=skills,
        related_index=related,
        semantic_scores={1: 0.99, 2: 0.99},
        semantic_reason="display_only",
    )
    dbt = plain.requirements[0]
    assert dbt.match_type == "related"
    assert dbt.mandatory_status == "missing"
    assert plain.mandatory_satisfied is False
    assert plain.fit_index > 0
    assert inflated.fit_index == plain.fit_index
    assert inflated.mandatory_satisfied is False
    with pytest.raises(ValueError, match="display-only"):
        Weights(semantic_similarity=0.4).validate()


def test_unknown_absent_unlisted_and_empty_profile() -> None:
    skills = {1: skill(1, "SQL"), 2: skill(2, "dbt")}
    requirements = [
        Requirement(1, 3, 5, True),
        Requirement(2, 3, 5, True),
    ]
    empty = score_profile_against_role(
        requirements=requirements,
        profile_skills=[],
        skills=skills,
        related_index={},
    )
    assert empty.fit_index == 0
    assert empty.mandatory_satisfied is False
    assert {row.presence for row in empty.requirements} == {"unlisted"}

    unknown = score_profile_against_role(
        requirements=[requirements[0]],
        profile_skills=[ProfileSkillState(1, None, "SQL")],
        skills=skills,
        related_index={},
    )
    assert unknown.requirements[0].presence == "unknown_level"
    assert unknown.requirements[0].mandatory_status == "unconfirmed"
    assert unknown.requirements[0].credit > 0
    assert unknown.mandatory_satisfied is False

    absent = score_profile_against_role(
        requirements=[requirements[0]],
        profile_skills=[ProfileSkillState(1, 0, "SQL")],
        skills=skills,
        related_index={},
    )
    assert absent.requirements[0].presence == "absent"
    assert absent.requirements[0].credit == 0
    assert absent.mandatory_satisfied is False


def test_level_gap_blocks_mandatory_satisfaction() -> None:
    skills = {1: skill(1, "Git")}
    result = score_profile_against_role(
        requirements=[Requirement(1, 3, 4, True)],
        profile_skills=[ProfileSkillState(1, 2, "Git")],
        skills=skills,
        related_index={},
    )
    assert result.requirements[0].match_type == "exact"
    assert result.requirements[0].mandatory_status == "level_gap"
    assert result.mandatory_satisfied is False
    assert 0 < result.fit_index < 100


def test_empty_requirement_list() -> None:
    result = score_profile_against_role(
        requirements=[],
        profile_skills=[],
        skills={},
        related_index={},
    )
    assert result.fit_index == 0
    assert result.mandatory_satisfied is True
    assert result.mandatory_total == 0


def test_score_is_deterministic_across_runs() -> None:
    skills = {
        1: skill(1, "PostgreSQL", ("Postgres",)),
        2: skill(2, "SQL"),
        3: skill(3, "dbt"),
    }
    related = {3: [RelatedEdge(other_skill_id=2, relation_type="related", weight=0.8)]}
    requirements = [
        Requirement(1, 3, 5, True),
        Requirement(2, 3, 3, False),
        Requirement(3, 3, 4, True),
    ]
    profile = [
        ProfileSkillState(1, 4, "Postgres"),
        ProfileSkillState(2, 5, "SQL"),
    ]
    first = score_profile_against_role(
        requirements=requirements,
        profile_skills=profile,
        skills=skills,
        related_index=related,
    )
    second = score_profile_against_role(
        requirements=requirements,
        profile_skills=profile,
        skills=skills,
        related_index=related,
    )
    assert first.as_dict() == second.as_dict()
    assert first.fit_index == second.fit_index
    assert [row.match_type for row in first.requirements] == [
        row.match_type for row in second.requirements
    ]
