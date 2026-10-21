"""Ontology integrity checks for the skill graph.

These checks are diagnostic. Seeded demo data may intentionally contain
prerequisite cycles (Legacy SOAP) so quality reports can surface them.
"""

from __future__ import annotations

from collections import defaultdict

from app.domain.aliases import normalize_alias

ALLOWED_RELATION_TYPES = frozenset(
    {"prerequisite", "related", "broader", "narrower", "requires", "teaches"}
)


def find_duplicate_aliases_within_skills(
    skills: list[tuple[int, str, tuple[str, ...] | list[str]]],
) -> list[dict[str, object]]:
    """Tokens repeated inside a single skill's canonical name + aliases."""

    findings: list[dict[str, object]] = []
    for skill_id, canonical, aliases in skills:
        seen: dict[str, int] = {}
        for token in [canonical, *list(aliases)]:
            folded = normalize_alias(token)
            if not folded:
                continue
            seen[folded] = seen.get(folded, 0) + 1
        duplicates = sorted(token for token, count in seen.items() if count > 1)
        if duplicates:
            findings.append(
                {
                    "skill_id": skill_id,
                    "canonical_name": canonical,
                    "duplicate_tokens": duplicates,
                }
            )
    return findings


def find_alias_collisions(
    skills: list[tuple[int, str, tuple[str, ...] | list[str]]],
) -> list[dict[str, object]]:
    """Tokens claimed by two different skills."""

    owners: dict[str, tuple[int, str]] = {}
    collisions: dict[str, list[tuple[int, str]]] = {}
    for skill_id, canonical, aliases in skills:
        for token in [canonical, *list(aliases)]:
            folded = normalize_alias(token)
            if not folded:
                continue
            previous = owners.get(folded)
            if previous is None:
                owners[folded] = (skill_id, canonical)
                continue
            if previous[0] == skill_id:
                continue
            bucket = collisions.setdefault(folded, [previous])
            if (skill_id, canonical) not in bucket:
                bucket.append((skill_id, canonical))
    return [
        {
            "token": token,
            "skills": [
                {"skill_id": skill_id, "canonical_name": name} for skill_id, name in claimants
            ],
        }
        for token, claimants in sorted(collisions.items())
    ]


def find_self_edges(relations: list[tuple[int, int, str]]) -> list[dict[str, object]]:
    return [
        {"source_skill_id": source, "target_skill_id": target, "relation_type": rel_type}
        for source, target, rel_type in relations
        if source == target
    ]


def find_invalid_edge_types(relations: list[tuple[int, int, str]]) -> list[dict[str, object]]:
    return [
        {"source_skill_id": source, "target_skill_id": target, "relation_type": rel_type}
        for source, target, rel_type in relations
        if rel_type not in ALLOWED_RELATION_TYPES
    ]


def find_orphan_skills(
    *,
    skill_ids: set[int],
    relations: list[tuple[int, int, str]],
    referenced_skill_ids: set[int],
) -> list[int]:
    """Skills with no edges and not referenced by roles/resources/profiles."""

    connected: set[int] = set()
    for source, target, _rel in relations:
        connected.add(source)
        connected.add(target)
    return sorted(skill_ids - connected - referenced_skill_ids)


def find_missing_prerequisite_targets(
    *,
    skill_ids: set[int],
    prerequisite_edges: list[tuple[int, int]],
) -> list[dict[str, int]]:
    """Prerequisite endpoints that point at unknown skill ids."""

    findings: list[dict[str, int]] = []
    for source, target in prerequisite_edges:
        if source not in skill_ids or target not in skill_ids:
            findings.append({"source_skill_id": source, "target_skill_id": target})
    return findings


def find_prerequisite_cycles(
    *,
    skill_ids: set[int],
    prerequisite_edges: list[tuple[int, int]],
    skill_names: dict[int, str],
    length_bound: int = 8,
    limit: int = 10,
) -> list[list[str]]:
    import networkx as nx

    graph = nx.DiGraph()
    graph.add_nodes_from(skill_ids)
    graph.add_edges_from(prerequisite_edges)
    cycles: list[list[str]] = []
    for cycle in nx.simple_cycles(graph, length_bound=length_bound):
        cycles.append([skill_names.get(skill_id, str(skill_id)) for skill_id in cycle])
        if len(cycles) >= limit:
            break
    return cycles


def find_broader_narrower_inconsistencies(
    relations: list[tuple[int, int, str]],
) -> dict[str, list[dict[str, object]]]:
    """Detect contradictory hierarchy edges.

    Seeded data stores ``broader`` without always storing the inverse ``narrower``.
    Missing inverses are reported separately as warnings, not hard conflicts.
    """

    broader_pairs: set[tuple[int, int]] = set()
    narrower_pairs: set[tuple[int, int]] = set()
    for source, target, rel_type in relations:
        if rel_type == "broader":
            broader_pairs.add((source, target))
        elif rel_type == "narrower":
            narrower_pairs.add((source, target))

    conflicts: list[dict[str, object]] = []
    for source, target in sorted(broader_pairs):
        if (source, target) in narrower_pairs:
            conflicts.append(
                {
                    "kind": "same_direction_broader_and_narrower",
                    "source_skill_id": source,
                    "target_skill_id": target,
                }
            )
        if source < target and (target, source) in broader_pairs:
            conflicts.append(
                {
                    "kind": "mutual_broader",
                    "source_skill_id": source,
                    "target_skill_id": target,
                }
            )

    missing_inverses: list[dict[str, object]] = []
    for source, target in sorted(broader_pairs):
        if (target, source) not in narrower_pairs:
            missing_inverses.append(
                {
                    "broader_source_id": source,
                    "broader_target_id": target,
                    "expected_narrower": {"source_skill_id": target, "target_skill_id": source},
                }
            )

    for source, target in sorted(narrower_pairs):
        if source < target and (target, source) in narrower_pairs:
            conflicts.append(
                {
                    "kind": "mutual_narrower",
                    "source_skill_id": source,
                    "target_skill_id": target,
                }
            )

    return {
        "conflicts": conflicts,
        "missing_narrower_inverses": missing_inverses,
    }


def audit_ontology(
    *,
    skills: list[tuple[int, str, tuple[str, ...] | list[str]]],
    relations: list[tuple[int, int, str]],
    prerequisite_edges: list[tuple[int, int]],
    referenced_skill_ids: set[int],
) -> dict[str, object]:
    skill_ids = {skill_id for skill_id, _name, _aliases in skills}
    skill_names = {skill_id: name for skill_id, name, _aliases in skills}
    hierarchy = find_broader_narrower_inconsistencies(relations)
    return {
        "duplicate_aliases_within_skills": find_duplicate_aliases_within_skills(skills),
        "alias_collisions": find_alias_collisions(skills),
        "self_edges": find_self_edges(relations),
        "invalid_edge_types": find_invalid_edge_types(relations),
        "orphan_skill_ids": find_orphan_skills(
            skill_ids=skill_ids,
            relations=relations,
            referenced_skill_ids=referenced_skill_ids,
        ),
        "missing_prerequisite_targets": find_missing_prerequisite_targets(
            skill_ids=skill_ids,
            prerequisite_edges=prerequisite_edges,
        ),
        "prerequisite_cycles": find_prerequisite_cycles(
            skill_ids=skill_ids,
            prerequisite_edges=prerequisite_edges,
            skill_names=skill_names,
        ),
        "broader_narrower_conflicts": hierarchy["conflicts"],
        "missing_narrower_inverses": hierarchy["missing_narrower_inverses"],
        "allowed_relation_types": sorted(ALLOWED_RELATION_TYPES),
    }


def relation_type_histogram(relations: list[tuple[int, int, str]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for _source, _target, rel_type in relations:
        counts[rel_type] += 1
    return dict(sorted(counts.items()))
