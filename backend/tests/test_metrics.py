import math

from app.domain.metrics import dcg, ndcg_at_k, precision_at_k
from app.domain.scoring import overlap_baseline_score, score_profile_against_role
from app.domain.types import ProfileSkillState, Requirement, SkillRecord


def test_ndcg_known_values() -> None:
    perfect = [3, 2, 0]
    assert ndcg_at_k(perfect, 3) == 1
    expected = dcg([3, 2, 0])
    assert expected == 3 / math.log2(2) + 2 / math.log2(3)
    # Ideal ranking of [0, 0, 3] is [3, 0, 0], so nDCG is 0.5.
    assert ndcg_at_k([0, 0, 3], 3) == (3 / math.log2(4)) / dcg([3, 0, 0])
    assert precision_at_k([3, 0, 0], 3) == 1 / 3
    assert ndcg_at_k([0, 0, 0], 3) == 1


def test_alias_ranker_beats_overlap_on_a_synonym_profile() -> None:
    skills = {
        1: SkillRecord(1, "PostgreSQL", ("Postgres",), "software"),
        2: SkillRecord(2, "JavaScript", ("js",), "software"),
        3: SkillRecord(3, "Git", (), "software"),
    }
    requirements = [
        Requirement(1, 3, 5, True),
        Requirement(2, 3, 4, True),
        Requirement(3, 3, 4, True),
    ]
    profile = [
        ProfileSkillState(1, 4, "Postgres"),
        ProfileSkillState(2, 4, "js"),
        ProfileSkillState(3, 3, "Git"),
    ]
    graph = score_profile_against_role(
        requirements=requirements,
        profile_skills=profile,
        skills=skills,
        related_index={},
    )
    overlap = overlap_baseline_score(requirements=requirements, profile_skills=profile, skills=skills)
    assert graph.coverage > overlap
    assert graph.mandatory_satisfied is True
