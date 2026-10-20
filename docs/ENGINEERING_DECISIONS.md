# Engineering decisions

Record of choices that shaped the SkillGraph MVP. Prefer this file over inventing new rationales in PRs.

## Stack

| Decision | Choice | Rationale |
| --- | --- | --- |
| Language / API | Python 3.12, FastAPI, Pydantic v2 | Typed request/response DTOs; matches portfolio HR stack |
| Persistence | SQLAlchemy 2 + Alembic; SQLite local, Postgres in CI | One model layer; `@pytest.mark.postgres` for dialect-only paths |
| Graph engine | NetworkX in-process cache | Enough for ~100 skills; no Neo4j ops cost for MVP |
| Frontend | React 19 + Vite + TypeScript + Tailwind 4 | Cytoscape for ontology; Recharts for match-type bars |
| Package managers | `uv` + `pnpm` | Locked, reproducible installs on Windows and CI |
| Ports | API `8105`, web `5105`, Postgres host `5405` | Avoid collisions with sibling portfolio apps |

## Deterministic scoring first

Embeddings (`sentence-transformers`) live in an optional extra. Torch, when installed, is CPU-indexed. `EMBEDDINGS_ENABLED=false` is the default. Semantic similarity has **composite weight 0** so it cannot hide a failed mandatory gate even when embeddings are on.

The demonstrable product — Graph Explorer, Role Explorer, Path Builder, evaluation — must work offline without downloading a model.

## Alias index with collision checks

Synonyms are first-class ontology data, not fuzzy string matching. Building the alias index fails fast on collisions so `js` cannot silently map to two skills. Scoring distinguishes `exact` vs `validated_synonym` so reviewers can see alias credit.

## Mandatory gate separate from fit index

A single blended “% ready for the job” number invites misuse. The UI and API always split:

1. Exploratory fit index (weighted coverage of stated requirements).
2. Mandatory satisfaction counts / statuses.

Related credit is intentionally weak (0.45 × edge weight) and never marks a mandatory skill satisfied.

## Cycle-safe paths instead of forced linearization

Prerequisite cycles are data bugs. SkillGraph surfaces them (`cycle_free=false`, cycle blocks) rather than inventing a topological order. That keeps learning-path demos honest when the ontology is imperfect.

## `graph_version` for multi-worker consistency

Ontology edits bump `graph_meta.graph_version` in the same transaction. Each request compares the cached NetworkX version and reloads when stale. Recommendation traces store the version so a later ontology change can explain score drift. Covered by `test_graph_version_visible_across_two_app_instances`.

## Loopback-first security posture

No auth in the MVP. Uvicorn binds `127.0.0.1` unless `ALLOW_NETWORK_BIND=true`. Compose maps use `127.0.0.1:` prefixes. Demo banner always shows “Local demo · synthetic data”.

## Evaluation honesty over marketing

Macro P@k / nDCG can **tie** between overlap and graph-augmented rankers while per-role coverage still differs. The overlap comparator is **canonical-name equality only** (no alias table) — so alias lifts show up in coverage, not necessarily in ranking metrics. Docs report measured macros and investigate cases — including where related edges do not improve top-k grade order and where overlap coverage is higher. Never hide equal aggregate metrics. See [EVALUATION.md](EVALUATION.md).

## Licensing

No `LICENSE` file yet. README states “License: pending owner decision”. Do not invent SPDX claims.

## Out of scope for this MVP

- Multi-tenant auth / SSO
- Production deployment / public live demo URL
- Claiming external taxonomy compliance (O\*NET, ESCO, etc.) without verified attribution
- Automatic employment decisions or person-level “worth” scores
