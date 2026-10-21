# SkillGraph algorithms

Deterministic MVP baseline (`method_version=skg-baseline-1.0.0`, `weights_version=weights-1.0.0`). Embeddings are optional and never required for recommendations or evaluation.

**Scope.** The fit index is an **exploratory coverage** of stated role requirements on a synthetic ontology. It is **not** a hiring probability, promotion odds, person-worth score, or automatic employment decision. Mandatory satisfaction is reported as a separate gate.

Implementation: `app/domain/aliases.py`, `app/domain/scoring.py`, `app/domain/paths.py`, `app/domain/constants.py`.

---

## Alias normalization

1. Lowercase, fold `&` → `and`, strip punctuation/spacing variants while keeping `+` and `#` so `C++` / `C#` stay distinct (`Postgres` → `postgres`, `ms excel` → `ms excel`, `C++` → `c++`).
2. Build a **collision-checked** alias index from canonical names + stored aliases. Two skills claiming the same token raise at index build time (`build_alias_index`).
3. Resolve profile asserted labels through the index before scoring (and when importing labels onto the profile).
4. Identity matches that arrive via alias are labeled `validated_synonym` (credit **0.95** × level factor), not exact (**1.0**). Exact requires the asserted label to normalize to the **canonical** name.

| Asserted label | Canonical | Match type |
| --- | --- | --- |
| `PostgreSQL` | PostgreSQL | `exact` |
| `Postgres` | PostgreSQL | `validated_synonym` |
| `js` | JavaScript | `validated_synonym` |

---

## Edge types

Persisted as `SkillRelation.relation_type`. How the runtime uses them:

| Type | Direction in seed | Used for scoring? | Used for paths? |
| --- | --- | --- | --- |
| `prerequisite` | prerequisite → dependent | no | yes — transitive expansion + SCC / topo order |
| `related` | undirected in cache | yes — soft credit | no |
| `broader` / `narrower` | stored typed; cache indexes both directions | yes — soft credit (same coefficient as related) | no |
| `requires` / `teaches` | ontology metadata / quality UI | no (not in fit index) | no |

Related / broader / narrower edges enter `related_index` with their stored **weight** (typically 0.3–1.0). Soft credit = `0.45 × edge.weight × level_factor`. Soft credit **never** satisfies a mandatory gate.

---

## Match credits

Per requirement, pick the best match in priority order:

| Match type | Credit | Satisfies mandatory? |
| --- | --- | --- |
| `exact` | `1.0 × level_factor` | yes when level met |
| `validated_synonym` | `0.95 × level_factor` | yes when level met |
| `related` (incl. broader/narrower via related index) | `0.45 × edge_weight × level_factor` | **never** |
| semantic similarity | display only (composite weight **0**) | **never** |
| `unlisted` / `absent` | `0` | no |

If a profile row exists for the required skill (and level ≠ 0), identity matching wins and related edges are not consulted for that requirement. Related credit applies only when the required skill is unlisted or explicitly absent (level 0).

### Level factor

| Profile level | Factor | Status |
| --- | ---: | --- |
| `null` (listed, unknown) | 0.5 | `unknown_level` |
| `0` (explicit absence) | 0.0 | `absent` |
| below target | `level / target` | `level_gap` |
| at or above target | 1.0 | `met` |

Unlisted skills are **unknown**, not definite absence — related credit may apply, but mandatory stays `missing`.

### Fit index arithmetic

For each requirement row, `credit` is as above. Let \(I_r\) be importance.

\[
\text{coverage} = \frac{\sum_r I_r \cdot \text{credit}_r}{\sum_r I_r}
\quad\text{(only exact + synonym + related contribute)}
\]

\[
\text{fit\_index} = \mathrm{round}(\text{coverage} \times 100,\ 1)
\]

Named components (`exact_match`, `validated_synonym`, `related_skill`) are the importance-weighted shares of those credits. `level_adequacy` is the average level factor on identity matches — already inside credits, **not** added again. Semantic mean is reported separately with composite weight 0.

---

## Mandatory gates

Mandatory status is independent of the fit index:

| Condition | `mandatory_status` |
| --- | --- |
| not mandatory | `not_applicable` |
| exact/synonym and level met | `satisfied` |
| exact/synonym and unknown level | `unconfirmed` |
| exact/synonym and level gap | `level_gap` |
| related / unlisted / absent / otherwise | `missing` |

API fields: `mandatory_satisfied`, `mandatory_satisfied_count`, `mandatory_total`. High related or semantic scores cannot flip a missing mandatory skill to satisfied.

---

## Overlap baseline (evaluation comparator)

`overlap_baseline_score` is intentionally weak:

- Counts a hit only when the profile’s **asserted label** normalizes to the requirement’s **canonical** name.
- **No** alias table, **no** related edges, **no** level factors.
- Score = hits / number of requirements (fraction of requirements with a raw name hit).

So `Postgres` does **not** hit `PostgreSQL` in the overlap baseline, while the graph ranker resolves it as `validated_synonym`. This is why alias-heavy fixtures show large **coverage** gaps even when macro P@k / nDCG tie.

---

## Explainable recommendation payload

`ScoreResult.as_dict()` (and `/api/recommendations`) exposes:

| Field | Role |
| --- | --- |
| `components.exact_match` / `validated_synonym` / `related_skill` | Fit-index contributions |
| `components.level_adequacy` | Average identity level factor (not re-added) |
| `components.evidence` | Counts of identity / related requirement rows |
| `components.semantic_similarity` | Display-only; composite weight 0 |
| `mandatory_gates` | Gate totals / status histogram |
| `missing_mandatories` | Unsatisfied mandatory rows (`skill_name`, `mandatory_status`, `match_type`) |

Related / semantic credit **never** flips `mandatory_status` to `satisfied`.

## Ontology integrity (`GET /api/ontology/quality`)

`app/domain/ontology_integrity.py` audits duplicate aliases, alias collisions, self-edges, invalid edge types, orphans, missing prerequisite endpoints, prerequisite cycles, and broader/narrower conflicts. Seeded `broader` edges without inverse `narrower` are counted as informational missing inverses, not hard conflicts. The intentional Legacy SOAP cycle remains visible under `prerequisite_cycles`.

## Versioned NetworkX cache (`graph_version`)

PostgreSQL / SQLite `graph_meta.graph_version` increments in the **same transaction** as ontology edits (skills, relations, roles). The in-memory NetworkX snapshot reloads when the version changes, so multiple API workers stay consistent. `/ready` and `GET /api/graph` expose the current version. Every recommendation and `RecommendationTrace` stores `graph_version`, `method_version`, and `weights_version`.

---

## Learning paths (cycle-safe)

1. Collect gaps: mandatory missing / level gap / unconfirmed, plus optional unlisted requirements the path builder includes.
2. Expand `prerequisite` edges transitive-closed over gaps (possessed non-gap skills pruned).
3. Build the induced Digraph; compute strongly connected components (NetworkX) and detect self-loops.
4. If a cycle touches the path, return `cycle_free=false`, list cycle blocks with `CYCLE_EXPLANATION`, and **refuse** to invent an order for those skills.
5. Otherwise topological-order the condensation DAG and attach learning resources (duration summed only where estimates exist).

Seed includes a deliberate cycle involving “Legacy SOAP” surfaces in `GET /api/ontology/quality` → `prerequisite_cycles`.

---

## Worked synthetic examples

### Example A — alias identity (mandatory can pass)

- Requirement: PostgreSQL, target 3, mandatory, importance 1.0  
- Profile: asserted `Postgres`, level 4  
- Normalize `postgres` → alias of PostgreSQL → `validated_synonym`  
- Level factor = 1.0 → credit = 0.95  
- `mandatory_status` = `satisfied`  
- Overlap baseline: asserted `postgres` ≠ canonical `postgresql` → **miss** (0 for that requirement)

### Example B — related credit cannot open a gate

- Requirement: dbt, target 3, mandatory  
- Profile: has SQL (related edge to dbt, weight 0.6), no dbt row  
- Match type `related`, credit = \(0.45 \times 0.6 \times 1.0 = 0.27\) (if SQL level ≥ target)  
- `mandatory_status` = **`missing`** even if fit index rises  
- Overlap baseline: also miss

### Example C — unknown level

- Requirement: Git, target 3, mandatory  
- Profile: Git listed, level `null`  
- Factor 0.5, credit 0.5 (exact) or 0.475 (synonym)  
- `mandatory_status` = `unconfirmed` — not treated as absence, not treated as satisfied

### Example D — cycle-safe path

- Gaps: `{A, B}`; edges `A→B` and `B→A`  
- SCC `{A,B}` → `cycle_free=false`, both skills in a cycle block, **no** ordered step invented  
- Acyclic `Data Modeling → ETL → Airflow` → ordered steps with resource estimates (demo Path Builder ~82h sum for Analytics Engineer gaps when estimates exist)

### Example E — fit index vs hiring language

Demo Role Explorer for Avery Chen → Analytics Engineer often lands near **46.1** exploratory fit with mandatory **3/7** incomplete. That number is coverage of stated requirements — **not** “46% chance of getting the job.”

---

## Ranking evaluation

`GET /api/evaluation` runs hand-labeled synthetic fixtures (`app/domain/gold.py`) through both rankers and reports macro Precision@3/5, Recall@3/5, nDCG@3/5. Labels are business-rule judgments on the synthetic ontology, not hiring outcomes. Unlabeled roles are excluded from each profile’s candidate set.

Measured numbers, why macros can tie, and per-role coverage cases: [EVALUATION.md](EVALUATION.md).

---

## Complexity notes (demo scale)

| Operation | Behavior at seed scale (~100 skills, ~100 edges) |
| --- | --- |
| Alias index build | O(skills + aliases); fails fast on token collisions |
| Score one role | O(requirements × related degree) over the related index |
| Learning path | Gap set expansion + SCC on the induced prerequisite digraph |
| Graph cache reload | Full NetworkX rebuild when `graph_version` changes |

These bounds are for the local demo catalog. They are not load-test claims for multi-tenant production.
