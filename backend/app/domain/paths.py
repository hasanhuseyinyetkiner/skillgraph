"""Prerequisite learning paths that refuse to linearize cycles."""

from __future__ import annotations

import networkx as nx

from app.domain.constants import CYCLE_EXPLANATION


def build_learning_path(
    *,
    gap_reasons: dict[int, str],
    possessed_skill_ids: set[int],
    prerequisite_edges: list[tuple[int, int]],
    skill_names: dict[int, str],
) -> dict[str, object]:
    """Order missing skills after their prerequisites.

    ``prerequisite_edges`` are ``(prerequisite_id, dependent_id)``.
    Skills in ``possessed_skill_ids`` are pruned unless they are themselves gaps
    (a level gap or an unconfirmed level). Strongly connected components with
    more than one skill, or a self-loop, are returned as cycle blocks and are
    not given a fake order.
    """

    if not gap_reasons:
        return {
            "timeline": [],
            "ordered_steps": [],
            "cycle_blocks": [],
            "cycle_free": True,
            "message": "No skill gaps for this role under the current profile.",
        }

    prerequisites: dict[int, list[int]] = {}
    for source, target in prerequisite_edges:
        prerequisites.setdefault(target, []).append(source)

    needed: set[int] = set()

    def include(skill_id: int) -> None:
        if skill_id in needed:
            return
        if skill_id in possessed_skill_ids and skill_id not in gap_reasons:
            return
        needed.add(skill_id)
        for prerequisite in prerequisites.get(skill_id, []):
            include(prerequisite)

    for skill_id in gap_reasons:
        include(skill_id)

    graph = nx.DiGraph()
    graph.add_nodes_from(sorted(needed))
    for source, target in prerequisite_edges:
        if source in needed and target in needed:
            graph.add_edge(source, target)

    index_of: dict[int, int] = {}
    members: list[set[int]] = []
    for component in nx.strongly_connected_components(graph):
        component_id = len(members)
        members.append(set(component))
        for node in component:
            index_of[node] = component_id

    condensation = nx.DiGraph()
    condensation.add_nodes_from(range(len(members)))
    for source, target in graph.edges:
        source_id = index_of[source]
        target_id = index_of[target]
        if source_id != target_id:
            condensation.add_edge(source_id, target_id)

    timeline: list[dict[str, object]] = []
    ordered_steps: list[dict[str, object]] = []
    cycle_blocks: list[dict[str, object]] = []
    for component_id in nx.topological_sort(condensation):
        nodes = members[component_id]
        cycled = len(nodes) > 1 or any(graph.has_edge(node, node) for node in nodes)
        if cycled:
            ordered = sorted(nodes, key=lambda node: skill_names.get(node, str(node)))
            block = {
                "kind": "cycle",
                "skill_ids": ordered,
                "skill_names": [skill_names.get(node, str(node)) for node in ordered],
                "explanation": CYCLE_EXPLANATION,
            }
            timeline.append(block)
            cycle_blocks.append(
                {
                    "skill_ids": ordered,
                    "skill_names": block["skill_names"],
                    "explanation": CYCLE_EXPLANATION,
                }
            )
            continue
        skill_id = next(iter(nodes))
        reason = gap_reasons.get(skill_id, "prerequisite")
        step = {
            "kind": "step",
            "skill_id": skill_id,
            "skill_name": skill_names.get(skill_id, str(skill_id)),
            "required": reason in {"mandatory_gap", "level_gap", "unconfirmed_level"},
            "reason": reason,
        }
        timeline.append(step)
        ordered_steps.append(step)

    return {
        "timeline": timeline,
        "ordered_steps": ordered_steps,
        "cycle_blocks": cycle_blocks,
        "cycle_free": not cycle_blocks,
        "message": (
            "Prerequisite cycle detected. The cyclic skills are reported and left unordered."
            if cycle_blocks
            else "Prerequisite graph for this path is acyclic."
        ),
    }
