"""Versioned scoring constants.

Changing a coefficient or the fit-index formula requires a new weights_version
or method_version. Semantic similarity is reported separately and has composite
weight 0 so it cannot hide a failed mandatory requirement.
"""

METHOD_VERSION = "skg-baseline-1.0.0"
WEIGHTS_VERSION = "weights-1.0.0"
DATASET_VERSION = "gold-fixtures-1.1.0"

EXACT_MATCH_CREDIT = 1.0
VALIDATED_SYNONYM_CREDIT = 0.95
RELATED_SKILL_CREDIT = 0.45
SEMANTIC_COMPOSITE_WEIGHT = 0.0
UNKNOWN_LEVEL_FACTOR = 0.5

FIT_INDEX_LABEL = "Exploratory fit index"
FIT_DISCLAIMER = (
    "Exploratory coverage of stated requirements on a synthetic ontology. "
    "This index is not a probability of getting a job, an employment decision, "
    "or a measure of a person."
)

LEVEL_SCALE: dict[str, str] = {
    "0": "Absent (explicit)",
    "1": "Awareness",
    "2": "Beginner",
    "3": "Working",
    "4": "Proficient",
    "5": "Expert",
    "unknown": "Unknown — listed without a level, not treated as absence",
    "unlisted": "Unlisted — not on the profile, not treated as definite absence",
}

CYCLE_EXPLANATION = (
    "These skills form a prerequisite cycle in the ontology. "
    "SkillGraph will not invent a learning order for them. "
    "Correct the prerequisite edges before treating this as a sequence."
)

COMPONENT_DEFINITIONS: tuple[dict[str, object], ...] = (
    {
        "key": "exact_match",
        "credit": EXACT_MATCH_CREDIT,
        "in_fit_index": True,
        "summary": "Profile row points at the required skill and the asserted label is the canonical name. Credit is the level factor.",
    },
    {
        "key": "validated_synonym",
        "credit": VALIDATED_SYNONYM_CREDIT,
        "in_fit_index": True,
        "summary": "Profile row points at the required skill via a stored alias such as Postgres for PostgreSQL. Credit is 0.95 times the level factor.",
    },
    {
        "key": "related_skill",
        "credit": RELATED_SKILL_CREDIT,
        "in_fit_index": True,
        "summary": "No identity match. Credit is 0.45 times the graph edge weight times the level factor of a broader, narrower, or related skill. This never satisfies a mandatory requirement.",
    },
    {
        "key": "level_adequacy",
        "credit": None,
        "in_fit_index": False,
        "summary": "Average level factor across identity matches. Already applied inside credits, so it is not added again.",
    },
    {
        "key": "evidence",
        "credit": None,
        "in_fit_index": False,
        "summary": "Counts of requirements with identity or related evidence. Credit weights live in exact/synonym/related contributions.",
    },
    {
        "key": "semantic_similarity",
        "credit": SEMANTIC_COMPOSITE_WEIGHT,
        "in_fit_index": False,
        "summary": "Optional embedding signal. Composite weight is 0. It is omitted entirely when embeddings are disabled.",
    },
)
