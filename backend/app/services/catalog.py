"""Load the ontology, score roles, and build learning paths."""

from __future__ import annotations

import io
import threading
import time
from collections import defaultdict
from dataclasses import dataclass

import networkx as nx
import pandas as pd
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db import bump_graph_version
from app.domain.aliases import build_alias_index, normalize_alias, resolve_skill_id
from app.domain.constants import (
    COMPONENT_DEFINITIONS,
    EXACT_MATCH_CREDIT,
    FIT_DISCLAIMER,
    FIT_INDEX_LABEL,
    LEVEL_SCALE,
    METHOD_VERSION,
    RELATED_SKILL_CREDIT,
    VALIDATED_SYNONYM_CREDIT,
    WEIGHTS_VERSION,
)
from app.domain.gold import GOLD_PROFILES
from app.domain.metrics import evaluate_rankers
from app.domain.paths import build_learning_path
from app.domain.scoring import score_profile_against_role
from app.domain.types import (
    ProfileSkillState,
    RelatedEdge,
    Requirement,
    SkillRecord,
    Weights,
)
from app.errors import DomainError
from app.models import (
    LearningResource,
    Profile,
    ProfileSkill,
    RecommendationTrace,
    Role,
    RoleRequirement,
    Skill,
    SkillRelation,
    utcnow,
)
from app.seed import reset_demo_profile
from app.settings import Settings

MAX_CSV_BYTES = 1_000_000
MAX_CSV_ROWS = 500
DURATION_NOTE = (
    "Sum includes only resources that publish an estimate. "
    "Missing estimates are counted, not treated as zero."
)


@dataclass(frozen=True)
class RelationRecord:
    id: int
    source_skill_id: int
    target_skill_id: int
    relation_type: str
    weight: float
    provenance: str


@dataclass(frozen=True)
class ResourceRecord:
    id: int
    title: str
    target_skill_id: int
    prerequisite_skill_ids: tuple[int, ...]
    duration_hours: float | None
    source: str


@dataclass
class RoleView:
    id: int
    title: str
    family: str
    summary: str
    requirements: list[Requirement]


@dataclass
class GraphSnapshot:
    version: int
    skills: dict[int, SkillRecord]
    skills_by_name: dict[str, SkillRecord]
    alias_index: dict[str, int]
    relations: list[RelationRecord]
    related_index: dict[int, list[RelatedEdge]]
    prerequisite_edges: list[tuple[int, int]]
    roles: dict[int, RoleView]
    roles_by_title: dict[str, RoleView]
    resources: list[ResourceRecord]
    graph: nx.DiGraph


class GraphCache:
    """In-memory NetworkX copy that reloads when graph_version changes."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._version = -1
        self._snapshot: GraphSnapshot | None = None

    def get(self, session: Session) -> GraphSnapshot:
        from app.db import current_graph_version

        current = current_graph_version(session)
        with self._lock:
            if self._snapshot is None or self._version != current:
                self._snapshot = load_snapshot(session, current)
                self._version = current
            return self._snapshot


def load_snapshot(session: Session, version: int | None = None) -> GraphSnapshot:
    from app.db import current_graph_version

    resolved_version = current_graph_version(session) if version is None else version
    skill_rows = session.scalars(select(Skill).order_by(Skill.id)).all()
    relation_rows = session.scalars(select(SkillRelation).order_by(SkillRelation.id)).all()
    role_rows = session.scalars(select(Role).order_by(Role.id)).all()
    requirement_rows = session.scalars(select(RoleRequirement)).all()
    resource_rows = session.scalars(select(LearningResource).order_by(LearningResource.id)).all()

    skills: dict[int, SkillRecord] = {}
    for row in skill_rows:
        skills[row.id] = SkillRecord(
            id=row.id,
            canonical_name=row.canonical_name,
            aliases=tuple(row.aliases or []),
            category=row.category,
            description=row.description or "",
            source=row.source,
            confidence=float(row.confidence),
        )
    skills_by_name = {skill.canonical_name: skill for skill in skills.values()}
    alias_index = build_alias_index(
        [(skill.id, skill.canonical_name, skill.aliases) for skill in skills.values()]
    )
    relations = [
        RelationRecord(
            id=row.id,
            source_skill_id=row.source_skill_id,
            target_skill_id=row.target_skill_id,
            relation_type=row.relation_type,
            weight=float(row.weight),
            provenance=row.provenance,
        )
        for row in relation_rows
    ]
    related_index: dict[int, list[RelatedEdge]] = defaultdict(list)
    prerequisite_edges: list[tuple[int, int]] = []
    graph = nx.DiGraph()
    for skill in skills.values():
        graph.add_node(f"skill:{skill.id}", kind="skill", label=skill.canonical_name)
    for relation in relations:
        graph.add_edge(
            f"skill:{relation.source_skill_id}",
            f"skill:{relation.target_skill_id}",
            relation_id=relation.id,
            relation_type=relation.relation_type,
            weight=relation.weight,
            provenance=relation.provenance,
        )
        if relation.relation_type == "prerequisite":
            prerequisite_edges.append((relation.source_skill_id, relation.target_skill_id))
        elif relation.relation_type in {"related", "broader", "narrower"}:
            forward = RelatedEdge(relation.target_skill_id, relation.relation_type, relation.weight)
            backward = RelatedEdge(relation.source_skill_id, relation.relation_type, relation.weight)
            related_index[relation.source_skill_id].append(forward)
            related_index[relation.target_skill_id].append(backward)
    requirements_by_role: dict[int, list[Requirement]] = defaultdict(list)
    for row in requirement_rows:
        requirements_by_role[row.role_id].append(
            Requirement(
                skill_id=row.skill_id,
                target_level=int(row.target_level),
                importance=float(row.importance),
                mandatory=bool(row.mandatory),
            )
        )
    roles = {
        row.id: RoleView(
            id=row.id,
            title=row.title,
            family=row.family,
            summary=row.summary,
            requirements=requirements_by_role.get(row.id, []),
        )
        for row in role_rows
    }
    resources = [
        ResourceRecord(
            id=row.id,
            title=row.title,
            target_skill_id=row.target_skill_id,
            prerequisite_skill_ids=tuple(int(item) for item in (row.prerequisite_skill_ids or [])),
            duration_hours=None if row.duration_hours is None else float(row.duration_hours),
            source=row.source,
        )
        for row in resource_rows
    ]
    return GraphSnapshot(
        version=resolved_version,
        skills=skills,
        skills_by_name=skills_by_name,
        alias_index=alias_index,
        relations=relations,
        related_index=related_index,
        prerequisite_edges=prerequisite_edges,
        roles=roles,
        roles_by_title={role.title: role for role in roles.values()},
        resources=resources,
        graph=graph,
    )


def semantic_availability(settings: Settings) -> tuple[dict[int, float] | None, str]:
    if not settings.embeddings_enabled:
        return None, "embeddings_disabled"
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        return None, "embeddings_extra_not_installed"
    return None, "embeddings_model_not_configured"


def weights_from_payload(payload: dict | None) -> Weights:
    if not payload:
        return Weights()
    try:
        weights = Weights(
            exact_match=float(payload.get("exact_match", EXACT_MATCH_CREDIT)),
            validated_synonym=float(payload.get("validated_synonym", VALIDATED_SYNONYM_CREDIT)),
            related_skill=float(payload.get("related_skill", RELATED_SKILL_CREDIT)),
            semantic_similarity=float(payload.get("semantic_similarity", 0)),
        )
        weights.validate()
    except (TypeError, ValueError) as exc:
        raise DomainError(str(exc), 400, "bad_weights") from exc
    return weights


def _profile_or_404(session: Session, profile_id: int) -> Profile:
    profile = session.get(Profile, profile_id)
    if profile is None:
        raise DomainError("Profile not found", 404, "not_found")
    return profile


def _role_or_404(snapshot: GraphSnapshot, role_id: int) -> RoleView:
    role = snapshot.roles.get(role_id)
    if role is None:
        raise DomainError("Role not found", 404, "not_found")
    return role


def load_profile_skills(session: Session, profile_id: int) -> list[ProfileSkillState]:
    rows = session.scalars(select(ProfileSkill).where(ProfileSkill.profile_id == profile_id)).all()
    return [
        ProfileSkillState(
            skill_id=row.skill_id,
            level=row.self_assessed_level,
            asserted_label=row.asserted_label,
        )
        for row in rows
    ]


def profile_payload(session: Session, profile: Profile, snapshot: GraphSnapshot) -> dict[str, object]:
    rows = session.scalars(select(ProfileSkill).where(ProfileSkill.profile_id == profile.id)).all()
    skills = []
    for row in rows:
        skill = snapshot.skills.get(row.skill_id)
        skills.append(
            {
                "skill_id": row.skill_id,
                "canonical_name": skill.canonical_name if skill else None,
                "category": skill.category if skill else None,
                "aliases": list(skill.aliases) if skill else [],
                "self_assessed_level": row.self_assessed_level,
                "asserted_label": row.asserted_label,
            }
        )
    skills.sort(key=lambda item: (item["canonical_name"] or "", item["skill_id"]))
    return {
        "id": profile.id,
        "slug": profile.slug,
        "display_name": profile.display_name,
        "summary": profile.summary,
        "synthetic": profile.synthetic,
        "consent_metadata": profile.consent_metadata,
        "skills": skills,
    }


def _score(
    snapshot: GraphSnapshot,
    profile_skills: list[ProfileSkillState],
    role: RoleView,
    settings: Settings,
    weights: Weights,
):
    semantic_scores, semantic_reason = semantic_availability(settings)
    return score_profile_against_role(
        requirements=role.requirements,
        profile_skills=profile_skills,
        skills=snapshot.skills,
        related_index=snapshot.related_index,
        weights=weights,
        semantic_scores=semantic_scores,
        semantic_reason=semantic_reason,
    )


def _match_type_counts(requirements: list[dict[str, object]]) -> dict[str, int]:
    frame = pd.DataFrame(requirements)
    if frame.empty or "match_type" not in frame.columns:
        return {}
    counts = frame.groupby("match_type", sort=True).size()
    return {str(key): int(value) for key, value in counts.items()}


def _trace(
    session: Session,
    *,
    profile: Profile,
    role: RoleView | None,
    snapshot: GraphSnapshot,
    profile_skills: list[ProfileSkillState],
    breakdown: dict[str, object],
    weights: Weights,
) -> int:
    trace = RecommendationTrace(
        profile_id=profile.id,
        role_id=None if role is None else role.id,
        graph_version=snapshot.version,
        method_version=METHOD_VERSION,
        weights_version=weights.version_label,
        input_snapshot={
            "profile_id": profile.id,
            "display_name": profile.display_name,
            "skills": [
                {
                    "skill_id": item.skill_id,
                    "level": item.level,
                    "asserted_label": item.asserted_label,
                    "canonical_name": snapshot.skills[item.skill_id].canonical_name
                    if item.skill_id in snapshot.skills
                    else None,
                }
                for item in profile_skills
            ],
            "role_id": None if role is None else role.id,
            "role_title": None if role is None else role.title,
        },
        score_breakdown=breakdown,
        created_at=utcnow(),
    )
    session.add(trace)
    session.flush()
    return int(trace.id)


def _recommendation_body(
    score,
    role: RoleView,
    snapshot: GraphSnapshot,
    profile_id: int,
    trace_id: int,
) -> dict[str, object]:
    body = score.as_dict()
    body.update(
        {
            "trace_id": trace_id,
            "graph_version": snapshot.version,
            "profile_id": profile_id,
            "role": {
                "id": role.id,
                "title": role.title,
                "family": role.family,
                "summary": role.summary,
            },
            "match_type_counts": _match_type_counts(body["requirements"]),  # type: ignore[arg-type]
        }
    )
    return body


def recommend(
    session_factory: sessionmaker[Session],
    cache: GraphCache,
    settings: Settings,
    *,
    profile_id: int,
    role_id: int,
    weights_payload: dict | None,
) -> dict[str, object]:
    weights = weights_from_payload(weights_payload)
    session = session_factory()
    try:
        snapshot = cache.get(session)
        profile = _profile_or_404(session, profile_id)
        role = _role_or_404(snapshot, role_id)
        profile_skills = load_profile_skills(session, profile.id)
        score = _score(snapshot, profile_skills, role, settings, weights)
        body = _recommendation_body(score, role, snapshot, profile.id, trace_id=0)
        trace_id = _trace(
            session,
            profile=profile,
            role=role,
            snapshot=snapshot,
            profile_skills=profile_skills,
            breakdown=body,
            weights=weights,
        )
        body["trace_id"] = trace_id
        trace = session.get(RecommendationTrace, trace_id)
        if trace is not None:
            trace.score_breakdown = body
        session.commit()
        return body
    finally:
        session.close()


def compare_roles(
    session_factory: sessionmaker[Session],
    cache: GraphCache,
    settings: Settings,
    *,
    profile_id: int,
    role_a_id: int,
    role_b_id: int,
) -> dict[str, object]:
    session = session_factory()
    try:
        snapshot = cache.get(session)
        profile = _profile_or_404(session, profile_id)
        role_a = _role_or_404(snapshot, role_a_id)
        role_b = _role_or_404(snapshot, role_b_id)
        profile_skills = load_profile_skills(session, profile.id)
        weights = Weights()
        score_a = _score(snapshot, profile_skills, role_a, settings, weights)
        score_b = _score(snapshot, profile_skills, role_b, settings, weights)
        body_a = _recommendation_body(score_a, role_a, snapshot, profile.id, 0)
        body_b = _recommendation_body(score_b, role_b, snapshot, profile.id, 0)
        trace_id = _trace(
            session,
            profile=profile,
            role=role_a,
            snapshot=snapshot,
            profile_skills=profile_skills,
            breakdown={"role_a": body_a, "role_b": body_b},
            weights=weights,
        )
        session.commit()

        def identity_names(score) -> set[str]:
            return {
                row.skill_name
                for row in score.requirements
                if row.match_type in {"exact", "validated_synonym"}
                and row.presence in {"matched", "unknown_level"}
            }

        def gap_names(score) -> set[str]:
            return {
                row.skill_name
                for row in score.requirements
                if row.mandatory and row.mandatory_status != "satisfied"
            }

        gaps_a = gap_names(score_a)
        gaps_b = gap_names(score_b)
        return {
            "trace_id": trace_id,
            "graph_version": snapshot.version,
            "method_version": METHOD_VERSION,
            "weights_version": weights.version_label,
            "disclaimer": FIT_DISCLAIMER,
            "role_a": body_a,
            "role_b": body_b,
            "shared_identity_skills": sorted(identity_names(score_a) & identity_names(score_b)),
            "only_a_mandatory_gaps": sorted(gaps_a - gaps_b),
            "only_b_mandatory_gaps": sorted(gaps_b - gaps_a),
        }
    finally:
        session.close()


def _resource_dict(resource: ResourceRecord, snapshot: GraphSnapshot) -> dict[str, object]:
    return {
        "id": resource.id,
        "title": resource.title,
        "duration_hours": resource.duration_hours,
        "duration_known": resource.duration_hours is not None,
        "source": resource.source,
        "prerequisite_skills": [
            snapshot.skills[skill_id].canonical_name
            for skill_id in resource.prerequisite_skill_ids
            if skill_id in snapshot.skills
        ],
    }


def learning_path(
    session_factory: sessionmaker[Session],
    cache: GraphCache,
    settings: Settings,
    *,
    profile_id: int,
    role_id: int,
) -> dict[str, object]:
    session = session_factory()
    try:
        snapshot = cache.get(session)
        profile = _profile_or_404(session, profile_id)
        role = _role_or_404(snapshot, role_id)
        profile_skills = load_profile_skills(session, profile.id)
        weights = Weights()
        score = _score(snapshot, profile_skills, role, settings, weights)
        reasons: dict[int, str] = {}
        requirements_by_skill = {item.skill_id: item for item in role.requirements}
        for row in score.requirements:
            if row.mandatory_status == "missing":
                reasons[row.skill_id] = "mandatory_gap"
            elif row.mandatory_status == "level_gap":
                reasons[row.skill_id] = "level_gap"
            elif row.mandatory_status == "unconfirmed":
                reasons[row.skill_id] = "unconfirmed_level"
            elif row.mandatory_status == "not_applicable" and (
                row.match_type in {"unlisted", "absent", "related"} or row.level_status == "level_gap"
            ):
                reasons[row.skill_id] = "level_gap" if row.level_status == "level_gap" else "optional_gap"
        possessed = {
            item.skill_id
            for item in profile_skills
            if item.level is None or item.level > 0
        }
        path = build_learning_path(
            gap_reasons=reasons,
            possessed_skill_ids=possessed,
            prerequisite_edges=snapshot.prerequisite_edges,
            skill_names={skill_id: skill.canonical_name for skill_id, skill in snapshot.skills.items()},
        )
        resources_by_skill: dict[int, list[ResourceRecord]] = defaultdict(list)
        for resource in snapshot.resources:
            resources_by_skill[resource.target_skill_id].append(resource)
        profile_by_skill = {item.skill_id: item for item in profile_skills}
        for item in path["timeline"]:  # type: ignore[union-attr]
            if item["kind"] == "step":
                skill = snapshot.skills[int(item["skill_id"])]
                requirement = requirements_by_skill.get(skill.id)
                profile_skill = profile_by_skill.get(skill.id)
                item["category"] = skill.category
                item["target_level"] = None if requirement is None else requirement.target_level
                item["profile_level"] = None if profile_skill is None else profile_skill.level
                item["resources"] = [
                    _resource_dict(resource, snapshot) for resource in resources_by_skill[skill.id]
                ]
            else:
                attached = []
                for skill_id in item["skill_ids"]:
                    attached.extend(
                        _resource_dict(resource, snapshot) for resource in resources_by_skill[int(skill_id)]
                    )
                item["resources"] = attached
        for step in path["ordered_steps"]:  # type: ignore[union-attr]
            skill_id = int(step["skill_id"])
            if "resources" not in step:
                step["resources"] = [
                    _resource_dict(resource, snapshot) for resource in resources_by_skill[skill_id]
                ]
        supplied: list[float] = []
        missing_duration = 0
        for step in path["ordered_steps"]:  # type: ignore[union-attr]
            for resource in step.get("resources", []):
                if resource["duration_hours"] is None:
                    missing_duration += 1
                else:
                    supplied.append(float(resource["duration_hours"]))
        body = {
            "graph_version": snapshot.version,
            "method_version": METHOD_VERSION,
            "weights_version": weights.version_label,
            "profile_id": profile.id,
            "role": {"id": role.id, "title": role.title, "family": role.family, "summary": role.summary},
            "fit_index": score.fit_index,
            "fit_index_label": FIT_INDEX_LABEL,
            "disclaimer": FIT_DISCLAIMER,
            "mandatory_satisfied": score.mandatory_satisfied,
            "timeline": path["timeline"],
            "ordered_steps": path["ordered_steps"],
            "cycle_blocks": path["cycle_blocks"],
            "cycle_free": path["cycle_free"],
            "message": path["message"],
            "duration_hours_supplied_sum": sum(supplied),
            "resources_missing_duration": missing_duration,
            "duration_note": DURATION_NOTE,
        }
        trace_id = _trace(
            session,
            profile=profile,
            role=role,
            snapshot=snapshot,
            profile_skills=profile_skills,
            breakdown={"kind": "learning_path", "cycle_free": path["cycle_free"], "message": path["message"]},
            weights=weights,
        )
        session.commit()
        body["trace_id"] = trace_id
        return body
    finally:
        session.close()


def profile_summary(
    session_factory: sessionmaker[Session],
    cache: GraphCache,
    settings: Settings,
    profile_id: int,
) -> dict[str, object]:
    session = session_factory()
    try:
        snapshot = cache.get(session)
        profile = _profile_or_404(session, profile_id)
        profile_skills = load_profile_skills(session, profile.id)
        weights = Weights()
        fits = []
        for role in snapshot.roles.values():
            score = _score(snapshot, profile_skills, role, settings, weights)
            fits.append(
                {
                    "role_id": role.id,
                    "title": role.title,
                    "family": role.family,
                    "fit_index": score.fit_index,
                    "mandatory_satisfied": score.mandatory_satisfied,
                    "mandatory_total": score.mandatory_total,
                    "mandatory_gap_count": score.mandatory_total - score.mandatory_satisfied_count,
                }
            )
        fits.sort(key=lambda item: (-float(item["fit_index"]), str(item["title"])))
        return {
            "profile": profile_payload(session, profile, snapshot),
            "skill_count": len(profile_skills),
            "fit_index_label": FIT_INDEX_LABEL,
            "disclaimer": FIT_DISCLAIMER,
            "ontology": {
                "skill_count": len(snapshot.skills),
                "role_count": len(snapshot.roles),
                "resource_count": len(snapshot.resources),
                "graph_version": snapshot.version,
            },
            "role_fits": fits,
        }
    finally:
        session.close()


def graph_payload(
    snapshot: GraphSnapshot,
    *,
    category: str | None,
    family: str | None,
    relation_type: str | None,
    query: str | None,
    limit: int,
) -> dict[str, object]:
    skills = list(snapshot.skills.values())
    roles = list(snapshot.roles.values())
    resources = list(snapshot.resources)
    if family:
        families = {item.strip() for item in family.split(",") if item.strip()}
        roles = [role for role in roles if role.family in families]
        seed_ids = {requirement.skill_id for role in roles for requirement in role.requirements}
        neighbor_ids = set(seed_ids)
        for skill_id in list(seed_ids):
            for source, target in snapshot.prerequisite_edges:
                if target == skill_id:
                    neighbor_ids.add(source)
        skills = [skill for skill in skills if skill.id in neighbor_ids]
        resources = [item for item in resources if item.target_skill_id in neighbor_ids]
    if category:
        categories = {item.strip() for item in category.split(",") if item.strip()}
        skills = [skill for skill in skills if skill.category in categories]
        skill_ids = {skill.id for skill in skills}
        roles = [role for role in roles if any(item.skill_id in skill_ids for item in role.requirements)]
        resources = [item for item in resources if item.target_skill_id in skill_ids]
    if query:
        needle = query.strip().lower()

        def hit(label: str) -> bool:
            return needle in label.lower()

        matched_skills = {
            skill.id
            for skill in skills
            if hit(skill.canonical_name) or any(hit(alias) for alias in skill.aliases)
        }
        expanded = set(matched_skills)
        for skill_id in list(matched_skills):
            for edge in snapshot.related_index.get(skill_id, []):
                expanded.add(edge.other_skill_id)
            for source, target in snapshot.prerequisite_edges:
                if source == skill_id:
                    expanded.add(target)
                if target == skill_id:
                    expanded.add(source)
        role_ids: set[int] = set()
        for role in roles:
            if hit(role.title) or any(item.skill_id in matched_skills for item in role.requirements):
                role_ids.add(role.id)
                for item in role.requirements:
                    expanded.add(item.skill_id)
        skills = [skill for skill in skills if skill.id in expanded]
        roles = [role for role in roles if role.id in role_ids]
        resources = [item for item in resources if item.target_skill_id in expanded or hit(item.title)]
    skills = skills[: max(limit, 0)]
    skill_ids = {skill.id for skill in skills}
    roles = [role for role in roles if any(item.skill_id in skill_ids for item in role.requirements)]
    resources = [item for item in resources if item.target_skill_id in skill_ids]
    nodes: list[dict[str, object]] = []
    for skill in skills:
        nodes.append(
            {
                "id": f"skill:{skill.id}",
                "entity_id": skill.id,
                "kind": "skill",
                "label": skill.canonical_name,
                "category": skill.category,
                "aliases": list(skill.aliases),
                "description": skill.description,
                "source": skill.source,
                "confidence": skill.confidence,
            }
        )
    for role in roles:
        nodes.append(
            {
                "id": f"role:{role.id}",
                "entity_id": role.id,
                "kind": "role",
                "label": role.title,
                "family": role.family,
                "summary": role.summary,
                "mandatory_skill_ids": [
                    item.skill_id for item in role.requirements if item.mandatory and item.skill_id in skill_ids
                ],
            }
        )
    for resource in resources:
        nodes.append(
            {
                "id": f"resource:{resource.id}",
                "entity_id": resource.id,
                "kind": "resource",
                "label": resource.title,
                "target_skill_id": resource.target_skill_id,
                "duration_hours": resource.duration_hours,
                "source": resource.source,
                "prerequisite_skill_ids": list(resource.prerequisite_skill_ids),
            }
        )
    edges: list[dict[str, object]] = []
    for relation in snapshot.relations:
        if relation.source_skill_id not in skill_ids or relation.target_skill_id not in skill_ids:
            continue
        if relation_type and relation.relation_type != relation_type:
            continue
        edges.append(
            {
                "id": f"rel:{relation.id}",
                "source": f"skill:{relation.source_skill_id}",
                "target": f"skill:{relation.target_skill_id}",
                "type": relation.relation_type,
                "weight": relation.weight,
                "provenance": relation.provenance,
            }
        )
    if relation_type is None:
        for role in roles:
            for requirement in role.requirements:
                if requirement.skill_id not in skill_ids:
                    continue
                edges.append(
                    {
                        "id": f"requires:{role.id}:{requirement.skill_id}",
                        "source": f"role:{role.id}",
                        "target": f"skill:{requirement.skill_id}",
                        "type": "requires",
                        "weight": requirement.importance / 5,
                        "provenance": "role-requirement",
                        "mandatory": requirement.mandatory,
                        "importance": requirement.importance,
                        "target_level": requirement.target_level,
                    }
                )
        for resource in resources:
            edges.append(
                {
                    "id": f"teaches:{resource.id}",
                    "source": f"resource:{resource.id}",
                    "target": f"skill:{resource.target_skill_id}",
                    "type": "teaches",
                    "weight": 1,
                    "provenance": resource.source,
                }
            )
    return {
        "graph_version": snapshot.version,
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "categories": sorted({skill.category for skill in snapshot.skills.values()}),
        "families": sorted({role.family for role in snapshot.roles.values()}),
        "relation_types": ["prerequisite", "related", "broader", "narrower", "requires", "teaches"],
    }


def ontology_quality(snapshot: GraphSnapshot) -> dict[str, object]:
    graph = nx.DiGraph()
    graph.add_nodes_from(snapshot.skills)
    for source, target in snapshot.prerequisite_edges:
        graph.add_edge(source, target)
    cycles: list[list[str]] = []
    for cycle in nx.simple_cycles(graph, length_bound=8):
        cycles.append([snapshot.skills[skill_id].canonical_name for skill_id in cycle])
        if len(cycles) >= 10:
            break
    alias_count = sum(len(skill.aliases) for skill in snapshot.skills.values())
    return {
        "skill_count": len(snapshot.skills),
        "role_count": len(snapshot.roles),
        "resource_count": len(snapshot.resources),
        "relation_count": len(snapshot.relations),
        "alias_count": alias_count,
        "alias_collisions": [],
        "prerequisite_cycles": cycles,
        "graph_version": snapshot.version,
        "synthetic": True,
        "source": "synthetic-seed-v1",
    }


def run_evaluation(snapshot: GraphSnapshot) -> dict[str, object]:
    requirements_by_title = {
        role.title: role.requirements for role in snapshot.roles.values()
    }
    report = evaluate_rankers(
        profiles=GOLD_PROFILES,
        roles=requirements_by_title,
        skills=snapshot.skills,
        skills_by_name=snapshot.skills_by_name,
        related_index=snapshot.related_index,
    )
    report["graph_version"] = snapshot.version
    report["method_version"] = METHOD_VERSION
    report["weights_version"] = WEIGHTS_VERSION
    return report


def heavy_analysis(session_factory: sessionmaker[Session], cache: GraphCache, delay_ms: int) -> dict[str, object]:
    if delay_ms:
        time.sleep(delay_ms / 1000)
    session = session_factory()
    try:
        snapshot = cache.get(session)
        return {
            "graph_version": snapshot.version,
            "nodes": snapshot.graph.number_of_nodes(),
            "edges": snapshot.graph.number_of_edges(),
        }
    finally:
        session.close()


def meta_payload(settings: Settings) -> dict[str, object]:
    banner = "Local demo · synthetic data" if settings.app_env == "demo" else None
    _scores, semantic_reason = semantic_availability(settings)
    return {
        "service": "skillgraph",
        "app_env": settings.app_env,
        "banner": banner,
        "embeddings_enabled": settings.embeddings_enabled,
        "semantic_reason": semantic_reason,
        "method_version": METHOD_VERSION,
        "weights_version": WEIGHTS_VERSION,
        "weights": {
            "exact_match": EXACT_MATCH_CREDIT,
            "validated_synonym": VALIDATED_SYNONYM_CREDIT,
            "related_skill": RELATED_SKILL_CREDIT,
            "semantic_similarity": 0.0,
        },
        "level_scale": LEVEL_SCALE,
        "component_definitions": list(COMPONENT_DEFINITIONS),
        "fit_index_label": FIT_INDEX_LABEL,
        "disclaimer": FIT_DISCLAIMER,
        "api_port": settings.port,
    }


def _assert_tokens_available(session: Session, skill_id: int | None, canonical: str, aliases: list[str]) -> None:
    rows = session.scalars(select(Skill)).all()
    payload: list[tuple[int, str, tuple[str, ...]]] = []
    for row in rows:
        if skill_id is not None and row.id == skill_id:
            continue
        payload.append((row.id, row.canonical_name, tuple(row.aliases or [])))
    payload.append((skill_id or -1, canonical, tuple(aliases)))
    try:
        build_alias_index(payload)
    except ValueError as exc:
        raise DomainError(str(exc), 409, "alias_collision") from exc


def list_skills(session: Session, query: str | None, category: str | None) -> list[dict[str, object]]:
    rows = session.scalars(select(Skill).order_by(Skill.canonical_name)).all()
    needle = (query or "").strip().lower()
    items = []
    for row in rows:
        if category and row.category != category:
            continue
        aliases = list(row.aliases or [])
        alias_hit = any(needle in alias.lower() for alias in aliases)
        if needle and needle not in row.canonical_name.lower() and not alias_hit:
            continue
        items.append(
            {
                "id": row.id,
                "canonical_name": row.canonical_name,
                "aliases": aliases,
                "category": row.category,
                "source": row.source,
                "confidence": row.confidence,
                "description": row.description,
            }
        )
    return items


def create_skill(session: Session, payload: dict[str, object]) -> dict[str, object]:
    canonical = str(payload["canonical_name"]).strip()
    aliases = [str(item).strip() for item in payload.get("aliases", []) if str(item).strip()]  # type: ignore[union-attr]
    if session.scalar(select(Skill.id).where(Skill.canonical_name == canonical)):
        raise DomainError("Skill already exists", 409, "duplicate")
    _assert_tokens_available(session, None, canonical, aliases)
    skill = Skill(
        canonical_name=canonical,
        aliases=aliases,
        category=str(payload["category"]).strip(),
        source=str(payload.get("source") or "user"),
        confidence=float(payload.get("confidence") or 0.5),
        description=str(payload.get("description") or ""),
    )
    session.add(skill)
    session.flush()
    version = bump_graph_version(session)
    session.commit()
    return {"id": skill.id, "canonical_name": skill.canonical_name, "graph_version": version}


def update_skill(session: Session, skill_id: int, payload: dict[str, object]) -> dict[str, object]:
    skill = session.get(Skill, skill_id)
    if skill is None:
        raise DomainError("Skill not found", 404, "not_found")
    aliases = skill.aliases
    if "aliases" in payload:
        aliases = [str(item).strip() for item in payload["aliases"] if str(item).strip()]  # type: ignore[union-attr]
    canonical = str(payload.get("canonical_name") or skill.canonical_name).strip()
    _assert_tokens_available(session, skill.id, canonical, list(aliases or []))
    skill.canonical_name = canonical
    skill.aliases = list(aliases or [])
    if "category" in payload:
        skill.category = str(payload["category"]).strip()
    if "description" in payload:
        skill.description = str(payload["description"])
    if "confidence" in payload and payload["confidence"] is not None:
        skill.confidence = float(payload["confidence"])
    version = bump_graph_version(session)
    session.commit()
    return {"id": skill.id, "canonical_name": skill.canonical_name, "aliases": skill.aliases, "graph_version": version}


def delete_skill(session: Session, skill_id: int) -> dict[str, object]:
    skill = session.get(Skill, skill_id)
    if skill is None:
        raise DomainError("Skill not found", 404, "not_found")
    session.execute(
        delete(SkillRelation).where(
            or_(SkillRelation.source_skill_id == skill_id, SkillRelation.target_skill_id == skill_id)
        )
    )
    try:
        session.delete(skill)
        version = bump_graph_version(session)
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise DomainError("Skill is still referenced by a role, resource, or profile", 409, "in_use") from exc
    return {"deleted": skill_id, "graph_version": version}


def create_relation(session: Session, payload: dict[str, object]) -> dict[str, object]:
    source = int(payload["source_skill_id"])
    target = int(payload["target_skill_id"])
    if source == target:
        raise DomainError("A relation needs two different skills", 400, "bad_relation")
    if session.get(Skill, source) is None or session.get(Skill, target) is None:
        raise DomainError("Skill not found", 404, "not_found")
    relation = SkillRelation(
        source_skill_id=source,
        target_skill_id=target,
        relation_type=str(payload["relation_type"]),
        weight=float(payload["weight"]),
        provenance=str(payload.get("provenance") or "user"),
    )
    session.add(relation)
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise DomainError("That relation already exists", 409, "duplicate") from exc
    version = bump_graph_version(session)
    session.commit()
    return {"id": relation.id, "graph_version": version}


def delete_relation(session: Session, relation_id: int) -> dict[str, object]:
    relation = session.get(SkillRelation, relation_id)
    if relation is None:
        raise DomainError("Relation not found", 404, "not_found")
    session.delete(relation)
    version = bump_graph_version(session)
    session.commit()
    return {"deleted": relation_id, "graph_version": version}


def list_roles(session: Session) -> list[dict[str, object]]:
    rows = session.scalars(select(Role).order_by(Role.title)).all()
    return [{"id": row.id, "title": row.title, "family": row.family, "summary": row.summary} for row in rows]


def get_role(session: Session, snapshot: GraphSnapshot, role_id: int) -> dict[str, object]:
    role = _role_or_404(snapshot, role_id)
    return {
        "id": role.id,
        "title": role.title,
        "family": role.family,
        "summary": role.summary,
        "requirements": [
            {
                "skill_id": item.skill_id,
                "skill_name": snapshot.skills[item.skill_id].canonical_name,
                "category": snapshot.skills[item.skill_id].category,
                "target_level": item.target_level,
                "importance": item.importance,
                "mandatory": item.mandatory,
            }
            for item in role.requirements
            if item.skill_id in snapshot.skills
        ],
    }


def create_role(session: Session, payload: dict[str, object]) -> dict[str, object]:
    title = str(payload["title"]).strip()
    if session.scalar(select(Role.id).where(Role.title == title)):
        raise DomainError("Role already exists", 409, "duplicate")
    role = Role(title=title, family=str(payload["family"]).strip(), summary=str(payload.get("summary") or ""))
    session.add(role)
    session.flush()
    for item in payload.get("requirements", []):  # type: ignore[union-attr]
        skill_id = int(item["skill_id"])
        if session.get(Skill, skill_id) is None:
            raise DomainError("Skill not found", 404, "not_found")
        session.add(
            RoleRequirement(
                role_id=role.id,
                skill_id=skill_id,
                target_level=int(item["target_level"]),
                importance=float(item["importance"]),
                mandatory=bool(item["mandatory"]),
            )
        )
    version = bump_graph_version(session)
    session.commit()
    return {"id": role.id, "title": role.title, "graph_version": version}


def _slug_for(session: Session, display_name: str) -> str:
    base = normalize_alias(display_name).replace(" ", "-")[:48] or "profile"
    slug = base
    suffix = 2
    while session.scalar(select(Profile.id).where(Profile.slug == slug)):
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


def create_profile(session: Session, display_name: str, summary: str) -> Profile:
    profile = Profile(
        slug=_slug_for(session, display_name),
        display_name=display_name.strip(),
        summary=summary,
        consent_metadata={
            "synthetic": True,
            "purpose": "local exploratory career sketch",
            "created_by": "api",
        },
        synthetic=True,
    )
    session.add(profile)
    session.commit()
    return profile


def update_profile(session: Session, profile_id: int, display_name: str | None, summary: str | None) -> Profile:
    profile = _profile_or_404(session, profile_id)
    if display_name is not None:
        profile.display_name = display_name.strip()
    if summary is not None:
        profile.summary = summary
    profile.synthetic = True
    session.commit()
    return profile


def delete_profile(session: Session, profile_id: int) -> None:
    profile = _profile_or_404(session, profile_id)
    session.delete(profile)
    session.commit()


def upsert_profile_skill(
    session: Session,
    snapshot: GraphSnapshot,
    profile_id: int,
    skill_id: int,
    level: int | None,
    asserted_label: str | None,
) -> dict[str, object]:
    profile = _profile_or_404(session, profile_id)
    skill = snapshot.skills.get(skill_id)
    if skill is None:
        raise DomainError("Skill not found", 404, "not_found")
    label = (asserted_label or "").strip() or skill.canonical_name
    row = session.scalar(
        select(ProfileSkill).where(
            ProfileSkill.profile_id == profile.id,
            ProfileSkill.skill_id == skill_id,
        )
    )
    if row is None:
        row = ProfileSkill(
            profile_id=profile.id,
            skill_id=skill_id,
            self_assessed_level=level,
            asserted_label=label,
        )
        session.add(row)
    else:
        row.self_assessed_level = level
        row.asserted_label = label
    session.commit()
    return {"profile_id": profile.id, "skill_id": skill_id, "self_assessed_level": level, "asserted_label": label}


def delete_profile_skill(session: Session, profile_id: int, skill_id: int) -> None:
    _profile_or_404(session, profile_id)
    row = session.scalar(
        select(ProfileSkill).where(
            ProfileSkill.profile_id == profile_id,
            ProfileSkill.skill_id == skill_id,
        )
    )
    if row is None:
        raise DomainError("Profile skill not found", 404, "not_found")
    session.delete(row)
    session.commit()


def parse_skill_csv(raw: bytes) -> list[dict[str, object]]:
    if len(raw) > MAX_CSV_BYTES:
        raise DomainError("CSV exceeds 1 MB", 413, "file_too_large")
    if b"\x00" in raw[:1024]:
        raise DomainError("CSV must be text", 415, "unsupported_type")
    try:
        frame = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False)
    except Exception as exc:
        raise DomainError("CSV could not be parsed", 400, "bad_csv") from exc
    if len(frame.index) > MAX_CSV_ROWS:
        raise DomainError("CSV exceeds 500 rows", 400, "too_many_rows")
    columns = {str(column).strip().lower(): column for column in frame.columns}
    if "skill" not in columns:
        raise DomainError("CSV must include a skill column", 400, "bad_csv")
    parsed: list[dict[str, object]] = []
    for record in frame.to_dict(orient="records"):
        label = str(record[columns["skill"]]).strip()
        if not label:
            continue
        level_raw = str(record[columns["level"]]).strip() if "level" in columns else ""
        level: int | None
        if level_raw == "" or level_raw.lower() == "unknown":
            level = None
        else:
            try:
                level = int(float(level_raw))
            except ValueError as exc:
                raise DomainError(f"Bad level for {label}", 400, "bad_csv") from exc
            if not 0 <= level <= 5:
                raise DomainError(f"Level out of range for {label}", 400, "bad_csv")
        parsed.append({"skill": label, "level": level})
    return parsed


def map_csv_rows(parsed: list[dict[str, object]], snapshot: GraphSnapshot) -> list[dict[str, object]]:
    mapped = []
    for row in parsed:
        label = str(row["skill"])
        skill_id = resolve_skill_id(label, snapshot.alias_index)
        skill = snapshot.skills.get(skill_id) if skill_id is not None else None
        if skill is None:
            match = "unknown"
        elif normalize_alias(label) == normalize_alias(skill.canonical_name):
            match = "canonical"
        else:
            match = "alias"
        mapped.append(
            {
                "input": label,
                "level": row["level"],
                "status": "mapped" if skill else "unknown",
                "match": match,
                "skill_id": None if skill is None else skill.id,
                "canonical_name": None if skill is None else skill.canonical_name,
            }
        )
    return mapped


def import_csv(
    session: Session,
    snapshot: GraphSnapshot,
    profile_id: int,
    raw: bytes,
    mode: str,
) -> dict[str, object]:
    profile = _profile_or_404(session, profile_id)
    mapped = map_csv_rows(parse_skill_csv(raw), snapshot)
    applied = 0
    if mode == "commit":
        for row in mapped:
            if row["skill_id"] is None:
                continue
            upsert_profile_skill(
                session,
                snapshot,
                profile.id,
                int(row["skill_id"]),
                row["level"] if isinstance(row["level"], int) or row["level"] is None else None,
                str(row["input"]),
            )
            applied += 1
    return {
        "mode": mode,
        "rows": mapped,
        "mapped_count": sum(1 for row in mapped if row["status"] == "mapped"),
        "unknown_count": sum(1 for row in mapped if row["status"] == "unknown"),
        "applied_count": applied,
    }


def export_profile(session: Session, snapshot: GraphSnapshot, profile_id: int) -> dict[str, object]:
    profile = _profile_or_404(session, profile_id)
    return {
        "synthetic": True,
        "exported_at": utcnow().isoformat(),
        "profile": profile_payload(session, profile, snapshot),
    }


def reset_demo(session: Session) -> Profile:
    count = session.scalar(select(func.count()).select_from(Skill))
    if not count:
        raise DomainError("Ontology is empty. Start the API so the seed can load.", 409, "empty_ontology")
    return reset_demo_profile(session)


def skill_count(session: Session) -> int:
    return int(session.scalar(select(func.count()).select_from(Skill)) or 0)
