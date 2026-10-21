"""Domain records used by scoring, paths, and evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.constants import (
    EXACT_MATCH_CREDIT,
    RELATED_SKILL_CREDIT,
    SEMANTIC_COMPOSITE_WEIGHT,
    VALIDATED_SYNONYM_CREDIT,
    WEIGHTS_VERSION,
)


@dataclass(frozen=True)
class SkillRecord:
    id: int
    canonical_name: str
    aliases: tuple[str, ...]
    category: str
    description: str = ""
    source: str = ""
    confidence: float = 0.0


@dataclass(frozen=True)
class ProfileSkillState:
    skill_id: int
    level: int | None
    asserted_label: str


@dataclass(frozen=True)
class Requirement:
    skill_id: int
    target_level: int
    importance: float
    mandatory: bool


@dataclass(frozen=True)
class RelatedEdge:
    other_skill_id: int
    relation_type: str
    weight: float


@dataclass(frozen=True)
class Weights:
    exact_match: float = EXACT_MATCH_CREDIT
    validated_synonym: float = VALIDATED_SYNONYM_CREDIT
    related_skill: float = RELATED_SKILL_CREDIT
    semantic_similarity: float = SEMANTIC_COMPOSITE_WEIGHT

    def validate(self) -> None:
        if self.semantic_similarity != 0:
            raise ValueError(
                "semantic_similarity is display-only and cannot take composite weight"
            )
        for name in ("exact_match", "validated_synonym", "related_skill"):
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")

    @property
    def version_label(self) -> str:
        default = Weights()
        if (
            self.exact_match == default.exact_match
            and self.validated_synonym == default.validated_synonym
            and self.related_skill == default.related_skill
            and self.semantic_similarity == default.semantic_similarity
        ):
            return WEIGHTS_VERSION
        return f"{WEIGHTS_VERSION}+override"


@dataclass
class RequirementScore:
    skill_id: int
    skill_name: str
    category: str
    mandatory: bool
    importance: float
    target_level: int
    match_type: str
    presence: str
    level_status: str
    profile_level: int | None
    asserted_label: str | None
    level_factor: float
    credit: float
    mandatory_status: str
    matched_via: dict[str, object] | None = None
    semantic_similarity: float | None = None
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "category": self.category,
            "mandatory": self.mandatory,
            "importance": self.importance,
            "target_level": self.target_level,
            "match_type": self.match_type,
            "presence": self.presence,
            "level_status": self.level_status,
            "profile_level": self.profile_level,
            "asserted_label": self.asserted_label,
            "level_factor": self.level_factor,
            "credit": self.credit,
            "mandatory_status": self.mandatory_status,
            "matched_via": self.matched_via,
            "semantic_similarity": self.semantic_similarity,
            "notes": list(self.notes),
        }


@dataclass
class ScoreResult:
    fit_index: float
    coverage: float
    weights: Weights
    requirements: list[RequirementScore]
    components: dict[str, object]
    mandatory_satisfied: bool
    mandatory_total: int
    mandatory_satisfied_count: int
    semantic_reason: str
    missing_mandatories: list[dict[str, object]] | None = None
    mandatory_gates: dict[str, object] | None = None

    def as_dict(self) -> dict[str, object]:
        from app.domain.constants import FIT_DISCLAIMER, FIT_INDEX_LABEL, METHOD_VERSION

        return {
            "fit_index": self.fit_index,
            "fit_index_label": FIT_INDEX_LABEL,
            "disclaimer": FIT_DISCLAIMER,
            "coverage": self.coverage,
            "method_version": METHOD_VERSION,
            "weights_version": self.weights.version_label,
            "weights": {
                "exact_match": self.weights.exact_match,
                "validated_synonym": self.weights.validated_synonym,
                "related_skill": self.weights.related_skill,
                "semantic_similarity": self.weights.semantic_similarity,
            },
            "components": self.components,
            "mandatory_satisfied": self.mandatory_satisfied,
            "mandatory_total": self.mandatory_total,
            "mandatory_satisfied_count": self.mandatory_satisfied_count,
            "mandatory_gates": self.mandatory_gates
            or {
                "all_satisfied": self.mandatory_satisfied,
                "total": self.mandatory_total,
                "satisfied_count": self.mandatory_satisfied_count,
                "missing_count": self.mandatory_total - self.mandatory_satisfied_count,
            },
            "missing_mandatories": list(self.missing_mandatories or []),
            "requirements": [row.as_dict() for row in self.requirements],
            "semantic": {
                "available": self.components.get("semantic_similarity", {}).get("value")
                is not None,
                "reason": self.semantic_reason,
            },
        }
