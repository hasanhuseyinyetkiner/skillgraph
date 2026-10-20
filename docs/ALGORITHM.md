# SkillGraph algorithms

Deterministic MVP baseline. Embeddings are optional and never required for recommendations or evaluation.

## Alias normalization

1. Lowercase, strip punctuation/spacing variants (`Postgres` → `postgres`).
2. Build a collision-checked alias index from canonical names + stored aliases.
3. Resolve profile asserted labels through the index before scoring.
4. Identity matches that arrive via alias are labeled `validated_synonym` (credit 0.95), not exact (1.0).

## Role fit scoring (`skg-baseline-1.0.0`)

Per requirement, pick the best match in order:

| Match type | Credit | Satisfies mandatory? |
| --- | --- | --- |
| exact | 1.0 × level factor | yes when level met |
| validated_synonym | 0.95 × level factor | yes when level met |
| related / broader / narrower | 0.45 × edge weight × level factor | **never** |
| semantic similarity | display only (composite weight 0) | **never** |

- **Level factor:** unknown level → 0.5; below target → `level/target`; otherwise 1.0.
- **Fit index:** importance-weighted sum of credits. Label: “Exploratory fit index”.
- **Mandatory gate:** reported separately. High related/semantic scores cannot hide a missing mandatory skill.
- **Overlap baseline:** identity matches only (no related edges). Used in evaluation as the weak comparator.

Every recommendation and `RecommendationTrace` stores `graph_version`, `method_version`, and `weights_version`.

## Versioned NetworkX cache

PostgreSQL / SQLite `graph_meta.graph_version` increments in the same transaction as ontology edits (skills, relations, roles). The in-memory NetworkX snapshot reloads when the version changes, so multiple API workers stay consistent.

## Learning paths

1. Collect mandatory/level gaps for the target role.
2. Expand prerequisite edges transitive-closed over gaps.
3. Detect strongly connected components / self-loops.
4. If a cycle touches the path, return `cycle_free=false`, list cycle blocks, and refuse to invent an order for those skills.
5. Otherwise topological-order remaining gaps and attach learning resources.

## Ranking evaluation

`GET /api/evaluation` runs hand-labeled synthetic fixtures (`app/domain/gold.py`) through both rankers and reports macro:

- Precision@3 / Precision@5
- Recall@3 / Recall@5
- nDCG@3 / nDCG@5

Labels are business-rule judgments on the synthetic ontology, not hiring outcomes. Unlabeled roles are excluded from each profile’s candidate set.
