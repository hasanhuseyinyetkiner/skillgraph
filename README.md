<a id="readme-top"></a>

<div align="center">

<p align="center">
  <img src="docs/assets/logo.png" alt="SkillGraph logo — Map skills. Unlock potential." width="560">
</p>

# SkillGraph

**Map what you know. Discover where your skills can take you.**

Explainable skill ontology, role-fit scoring with named match types, and cycle-safe learning paths. Deterministic by default; embeddings optional. Accent `#C026D3`.

[![CI](https://github.com/hasanhuseyinyetkiner/skillgraph/actions/workflows/ci.yml/badge.svg)](https://github.com/hasanhuseyinyetkiner/skillgraph/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Overview](#why-it-exists) · [Demo](#demo) · [Architecture](#architecture) · [Algorithm](#scoring-and-paths) · [Evaluation](#evaluation) · [Quick start](#quick-start) · [Docs](#documentation)

</div>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/screenshots/graph-explorer-dark.png">
    <img alt="Graph Explorer with taxonomy rail, Cytoscape canvas, and adjacency panel" src="docs/screenshots/graph-explorer-light.png" width="100%">
  </picture>
</p>

---

## For HR and talent leaders

| Question | What this tool gives you |
| --- | --- |
| **How close is a profile to a role?** | A fit index with named match types: exact, validated synonym, related. |
| **Are mandatory skills respected?** | Related skills never satisfy a mandatory requirement. Gaps are reported separately. |
| **What should be learned next?** | Cycle-safe learning paths with resources. Cycles are reported, not hidden. |
| **What it is not** | Not a hiring probability and not a promotion or rejection decision. Synthetic profiles only. |

## Why it exists

Internal mobility tools often hide the ontology and the score. Reviewers cannot see why a role ranked where it did.

SkillGraph keeps the graph, match types, and mandatory gates visible. Fit index is an exploratory coverage measure — not a hiring probability or person score.

**Who it is for:** engineers reviewing knowledge-graph / recommender design; HR-tech reviewers checking explainable career-path demos.

**Status:** local MVP / demo. Loopback bind by default. No multi-user auth.

## Scope

| In scope | Out of scope |
| --- | --- |
| Synthetic demo profile, ontology seed, aliases | Real employee data or live HR systems |
| Deterministic role-fit + named components | Auto promotion / rejection decisions |
| Cycle-safe learning paths | Forced path order when prerequisites cycle |
| P@k / nDCG on ten hand-labeled fixtures | Claiming hiring-outcome prediction |
| Optional embeddings (composite weight 0) | Requiring a model download for the demo |
| SQLite local / Postgres in CI | Multi-tenant auth / public SaaS |

Seed (local SQLite): **97** skills, **24** roles, **36** learning resources, **103** relations.

## Capabilities

| Area | Status | Notes |
| --- | --- | --- |
| Skills inventory | Shipped | Demo profile (Avery Chen); export / erase / reset |
| Ontology | Shipped | Aliases; prerequisite / related / broader / narrower |
| Graph Explorer | Shipped | Cytoscape + category taxonomy + adjacency inspector |
| Role Explorer | Shipped | Gap matrix, evidence weight bars, role compare |
| Path Builder | Shipped | Cycle-safe prerequisite order + resources |
| Evaluation | Shipped | P@k / R@k / nDCG@k on `gold-fixtures-1.1.0` (10 profiles); honest tie flags |
| Ontology integrity | Shipped | Alias collisions, self-edges, orphans, cycles, broader/narrower audit |
| Versioned cache | Shipped | `graph_version` across API workers |
| Embeddings | Optional | Off by default; composite weight `0` when present |
| Multi-user auth | Not shipped | Loopback demo only |
| Local Docker Compose | **BLOCKED** on this host | CI still defines `compose-smoke`; do not claim local Docker success |

## Architecture

```mermaid
%%{init: {
  "theme": "base",
  "themeVariables": {
    "primaryColor": "#C026D3",
    "primaryTextColor": "#ffffff",
    "primaryBorderColor": "#86198F",
    "lineColor": "#C026D3",
    "secondaryColor": "#FAE8FF",
    "tertiaryColor": "#FDF4FF",
    "fontFamily": "IBM Plex Sans, ui-sans-serif, system-ui, sans-serif"
  }
}}%%
flowchart LR
  PG[(Skills / roles / edges)] --> META[graph_version]
  META --> NX[NetworkX cache]
  NX --> R[Deterministic recommender]
  R --> P[Cycle-safe learning path]
  NX --> UI[Cytoscape + adjacency UI]
  R --> T[RecommendationTrace]
  R --> EVAL[P@k / nDCG@k fixtures]
```

| Layer | Choice | Why |
| --- | --- | --- |
| API | FastAPI + SQLAlchemy 2 + Alembic | Typed DTOs, migrations, `/health` + `/ready` |
| Graph | NetworkX snapshot keyed by `graph_version` | Reload on ontology edits without Neo4j |
| Scoring | Pure Python domain module | Unit-testable; embeddings never required |
| UI | React + Vite + Cytoscape + Recharts | Graph explorer + gap / evidence views |
| Data | SQLite local / Postgres in CI | Same models; compose verified in `compose-smoke` |

Deep dive: [docs/ALGORITHM.md](docs/ALGORITHM.md) · [docs/EVALUATION.md](docs/EVALUATION.md).

## Quick start

Native path on Windows 11 with `uv` + `pnpm`. Local Docker Compose is **BLOCKED** on the authoring host; the `compose-smoke` CI job remains defined for machines with Docker.

```powershell
# Backend — http://127.0.0.1:8105
cd backend
uv sync
uv run python -m app

# Frontend — http://127.0.0.1:5105 (new terminal)
cd frontend
pnpm install
pnpm dev
```

| Service | URL |
| --- | --- |
| Web | http://127.0.0.1:5105 |
| API docs | http://127.0.0.1:8105/docs |
| Health | http://127.0.0.1:8105/health |
| Ready | http://127.0.0.1:8105/ready |

Default DB: `backend/data/skillgraph.db`. Overrides: [`.env.example`](.env.example) / [`frontend/.env.example`](frontend/.env.example). Prefer one local API process against the default SQLite file.

## Demo

1. Open http://127.0.0.1:5105 — demo banner + profile **Avery Chen**.
2. **Graph Explorer** — pick a category, select a node, inspect adjacency by relation type.
3. **Role Explorer** → **Analytics Engineer** → **Compute role fit** — gap matrix + evidence weights (`exact_match`, `validated_synonym`, `related_skill`, …). Label is an exploratory fit index, **not** a hiring probability.
4. **Path Builder** → same role → **Build path** — ordered gap steps when cycle-free; cycles are reported, not invented away.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/screenshots/role-explorer-dark.png">
    <img alt="Role Explorer gap matrix and evidence weight breakdown for Analytics Engineer" src="docs/screenshots/role-explorer-light.png" width="100%">
  </picture>
</p>

Playwright covers the same arc: `demo profile → graph → role fit → learning path` (`frontend/e2e/demo-flow.spec.ts`) plus an a11y smoke (`frontend/e2e/a11y-smoke.spec.ts`). CI runs `pnpm test:e2e` (WFO-style job).

## Scoring and paths

**Alias normalization.** Labels fold to a collision-checked token (`Postgres` → `postgres`). Identity via alias is `validated_synonym` (0.95× level factor), not exact (1.0).

**Mandatory gates.** Related / semantic credit **never** satisfies a mandatory requirement. The gate is reported separately from the fit index.

**Cycle-safe paths.** Prerequisite expansion + SCC detection. If a cycle touches the path, `cycle_free=false` and those skills get no invented order.

**`graph_version`.** Incremented in the same transaction as ontology edits; NetworkX reloads when the version changes; every recommendation and trace records it.

Full rules: [docs/ALGORITHM.md](docs/ALGORITHM.md).

## Evaluation

Measured via `GET /api/evaluation` on **ten** hand-labeled synthetic profiles (`method_version=skg-baseline-1.0.0`, `dataset_version=gold-fixtures-1.1.0`). Grades are fixture judgments on the demo ontology — **not** hiring outcomes.

| Method | P@3 | P@5 | R@3 | R@5 | nDCG@3 | nDCG@5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Overlap baseline | 0.8667 | 0.8400 | 0.5175 | 0.9092 | 0.8152 | 0.8908 |
| Graph-augmented | 0.9000 | 0.8400 | 0.6175 | 0.9092 | 0.9383 | 0.9684 |

**Honest read:** on this expanded set `macro_metrics_tie=false` — graph is higher on P@3 / R@3 / nDCG@3 / nDCG@5; P@5 and R@5 still match. The original five fixtures still show identical top-k grade sequences; divergence comes from cold-start / missing-mandatory / misleading-related scenarios. Related credit **never** satisfies mandatory gates. Do not market these numbers as hiring prediction. Full analysis: [docs/EVALUATION.md](docs/EVALUATION.md).

## API

```powershell
curl http://127.0.0.1:8105/ready
curl http://127.0.0.1:8105/api/profiles/demo
curl -X POST http://127.0.0.1:8105/api/recommendations -H "Content-Type: application/json" -d "{\"profile_id\":1,\"role_id\":1}"
curl -X POST http://127.0.0.1:8105/api/learning-paths -H "Content-Type: application/json" -d "{\"profile_id\":1,\"role_id\":1}"
curl http://127.0.0.1:8105/api/evaluation
```

Key routes: `/api/skills`, `/api/graph`, `/api/roles`, `/api/profiles/*`, `/api/recommendations`, `/api/recommendations/compare`, `/api/learning-paths`, `/api/ontology/quality`, `/api/evaluation`, `/health`, `/ready`.

## Testing

```powershell
cd backend
uv run ruff check .
uv run pytest -q

cd ../frontend
pnpm lint
pnpm test
pnpm build
pnpm exec playwright install chromium   # once
pnpm e2e
pnpm screenshots   # writes docs/screenshots/*.png
```

| Check | Result (2026-10-21) |
| --- | --- |
| `uv run pytest -q` | **47 passed**, 1 skipped (Postgres marker) |
| `pnpm test` (Vitest) | **1 passed** |
| Eval metrics | Live `GET /api/evaluation` (table above) |
| Playwright | **2 passed** critical+a11y (`demo-flow`, `a11y-smoke`); screenshots via `pnpm screenshots` (real captures refreshed this session); CI `e2e` job added |
| Local Docker Compose | **BLOCKED** (no Docker on this host) |

`compose.yaml` binds API `127.0.0.1:8105`, web `127.0.0.1:5105`, Postgres host `5405`. CI runs markdown-links, Ruff + pytest (Postgres service), frontend lint/tsc/vitest/build, Playwright `e2e`, and `compose-smoke`.

## Security, privacy, and limitations

> [!IMPORTANT]
> Synthetic profiles only. Fit scores are exploratory — never a probability of getting a job, a promotion decision, or a person score. No protected attributes are used.

Policy: [`SECURITY.md`](SECURITY.md).

- Loopback bind by default (`ALLOW_NETWORK_BIND=true` required otherwise).
- No multi-user auth in this MVP.
- External taxonomies are not claimed; seed data is synthetic/attributed in-code.
- Embeddings optional; demo and evaluation run with `EMBEDDINGS_ENABLED=false`.
- Macro metrics can tie even when per-role coverage changes — see [docs/EVALUATION.md](docs/EVALUATION.md).

## Documentation

| Doc | Contents |
| --- | --- |
| [`docs/ALGORITHM.md`](docs/ALGORITHM.md) | Normalization, edge types, credits, gates, paths |
| [`docs/EVALUATION.md`](docs/EVALUATION.md) | Expanded fixtures, macro non-tie, grade-sequence ties |
| [`docs/PERFORMANCE_BASELINE.md`](docs/PERFORMANCE_BASELINE.md) | Measured fit/path/eval latency (SQLite local) |
| [`SECURITY.md`](SECURITY.md) | Loopback demo boundaries; not a production security claim |
| [`frontend/README.md`](frontend/README.md) | Frontend setup, scripts, pages |
| [`LICENSE`](LICENSE) | MIT © 2026 Hasan Hüseyin Yetkiner |

<p align="right"><a href="#readme-top">↑ back to top</a></p>
