"""Load the synthetic ontology and the demo profile."""

from __future__ import annotations

import networkx as nx
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db import bump_graph_version
from app.domain.aliases import build_alias_index
from app.models import (
    LearningResource,
    Profile,
    ProfileSkill,
    Role,
    RoleRequirement,
    Skill,
    SkillRelation,
)
from app.seed_data import (
    CONFIDENCE,
    CONSENT,
    DEMO_PROFILE,
    RELATIONS,
    RESOURCES,
    ROLES,
    SKILLS,
    SOURCE,
)


def validate_seed_spec() -> None:
    names = [row[0] for row in SKILLS]
    if len(names) < 80:
        raise RuntimeError(f"expected at least 80 skills, found {len(names)}")
    if len(names) != len(set(names)):
        raise RuntimeError("duplicate skill name in seed")
    if len(ROLES) < 20:
        raise RuntimeError(f"expected at least 20 roles, found {len(ROLES)}")
    if len(RESOURCES) < 30:
        raise RuntimeError(f"expected at least 30 resources, found {len(RESOURCES)}")
    if len({title for title, *_rest in ROLES}) != len(ROLES):
        raise RuntimeError("duplicate role title in seed")
    build_alias_index([(index, name, aliases) for index, (name, _category, aliases, _note) in enumerate(SKILLS)])
    known = set(names)
    for source, target, relation_type, weight in RELATIONS:
        if source not in known or target not in known:
            raise RuntimeError(f"relation endpoint missing: {source} -> {target}")
        if relation_type not in {"prerequisite", "related", "broader", "narrower"}:
            raise RuntimeError(f"unknown relation type {relation_type}")
        if not 0 < weight <= 1:
            raise RuntimeError(f"bad weight for {source} -> {target}")
    for title, _family, _summary, requirements in ROLES:
        for skill_name, level, importance, _mandatory in requirements:
            if skill_name not in known:
                raise RuntimeError(f"{title} requires unknown skill {skill_name}")
            if not 0 <= level <= 5 or importance <= 0:
                raise RuntimeError(f"bad requirement on {title} / {skill_name}")
    for title, target, prerequisites, _hours in RESOURCES:
        if target not in known or any(item not in known for item in prerequisites):
            raise RuntimeError(f"resource {title} points at an unknown skill")
    for skill_name, _level, _label in DEMO_PROFILE["skills"]:
        if skill_name not in known:
            raise RuntimeError(f"demo profile lists unknown skill {skill_name}")
    graph = nx.DiGraph()
    graph.add_nodes_from(names)
    for source, target, relation_type, _weight in RELATIONS:
        if relation_type == "prerequisite":
            graph.add_edge(source, target)
    cycles = list(nx.simple_cycles(graph, length_bound=8))
    if not any("Legacy SOAP" in cycle for cycle in cycles):
        raise RuntimeError("seed is missing the Legacy SOAP prerequisite cycle")


def _skill_description(category: str, note: str) -> str:
    if note:
        return note
    return f"Synthetic {category} skill in the local demo ontology."


def seed_ontology(session: Session) -> None:
    validate_seed_spec()
    existing = session.scalar(select(func.count()).select_from(Skill))
    if existing:
        return
    by_name: dict[str, Skill] = {}
    for name, category, aliases, note in SKILLS:
        skill = Skill(
            canonical_name=name,
            aliases=list(aliases),
            category=category,
            source=SOURCE,
            confidence=CONFIDENCE,
            description=_skill_description(category, note),
        )
        session.add(skill)
        by_name[name] = skill
    session.flush()
    for source, target, relation_type, weight in RELATIONS:
        session.add(
            SkillRelation(
                source_skill_id=by_name[source].id,
                target_skill_id=by_name[target].id,
                relation_type=relation_type,
                weight=weight,
                provenance=SOURCE,
            )
        )
    for title, family, summary, requirements in ROLES:
        role = Role(title=title, family=family, summary=summary)
        session.add(role)
        session.flush()
        for skill_name, level, importance, mandatory in requirements:
            session.add(
                RoleRequirement(
                    role_id=role.id,
                    skill_id=by_name[skill_name].id,
                    target_level=level,
                    importance=importance,
                    mandatory=mandatory,
                )
            )
    for title, target, prerequisites, hours in RESOURCES:
        session.add(
            LearningResource(
                title=title,
                target_skill_id=by_name[target].id,
                prerequisite_skill_ids=[by_name[name].id for name in prerequisites],
                duration_hours=hours,
                source="synthetic catalog",
            )
        )
    _write_demo_profile(session, by_name)
    bump_graph_version(session)
    session.commit()


def _write_demo_profile(session: Session, by_name: dict[str, Skill]) -> Profile:
    profile = session.scalar(select(Profile).where(Profile.slug == DEMO_PROFILE["slug"]))
    if profile is None:
        profile = Profile(
            slug=str(DEMO_PROFILE["slug"]),
            display_name=str(DEMO_PROFILE["display_name"]),
            summary=str(DEMO_PROFILE["summary"]),
            consent_metadata=dict(CONSENT),
            synthetic=True,
        )
        session.add(profile)
        session.flush()
    else:
        profile.display_name = str(DEMO_PROFILE["display_name"])
        profile.summary = str(DEMO_PROFILE["summary"])
        profile.consent_metadata = dict(CONSENT)
        profile.synthetic = True
        session.execute(delete(ProfileSkill).where(ProfileSkill.profile_id == profile.id))
        session.flush()
    for skill_name, level, label in DEMO_PROFILE["skills"]:
        session.add(
            ProfileSkill(
                profile_id=profile.id,
                skill_id=by_name[skill_name].id,
                self_assessed_level=level,
                asserted_label=label,
            )
        )
    return profile


def reset_demo_profile(session: Session) -> Profile:
    skills = {skill.canonical_name: skill for skill in session.scalars(select(Skill))}
    profile = _write_demo_profile(session, skills)
    session.commit()
    return profile


def seed_if_empty(session_factory: sessionmaker[Session]) -> None:
    session = session_factory()
    try:
        seed_ontology(session)
    finally:
        session.close()
